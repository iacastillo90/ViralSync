"""
publisher_task.py

Tarea asíncrona Celery para la auto-publicación multi-canal (Instagram Reels, TikTok, YouTube Shorts).
Escanea la base de datos PostgreSQL en busca de videos agendados cuyo tiempo de publicación haya vencido
y ejecuta la llamada a la Meta Graph API para publicar el video de forma 100% autónoma.

S3 — Auto-Publicación (REQ-PUB-02/04/07): el task ya NO duplica llamadas directas a la
Meta Graph API; delega al microservicio outbound `:8002` con el MISMO contrato de
`agents/nodes/publish.py` (`POST {PUBLISHER_URL}/publish`), con credenciales tenant-first
(`instagram_graph_api_token_ref` / `instagram_business_account_id`, fallback a env en dev)
y routing por `video.platform` (PublisherFactory del micro).
Idempotencia (REQ-PUB-04): tras publicar, el video pasa a `publish_approval_status='published'`
y deja de matchear la query de videos 'approved' vencidos; además el micro dedupea por
idempotency_key (RESILIENCE-001).

`_publish_to_instagram_reels` se conserva como helper legacy (compatibilidad con
test_auto_publisher); el flujo productivo no lo usa.
"""

import os
import hashlib
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any

from workers.celery_app import celery_app
from backend.db.session import AsyncSessionLocal
from backend.db.models import Video, Script, Idea, Tenant
from sqlalchemy import or_, select

logger = logging.getLogger(__name__)

META_GRAPH_API_URL = os.getenv("META_GRAPH_API_URL", "https://graph.facebook.com/v19.0")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "dev_instagram_account_123")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "dev_meta_access_token_456")

# Microservicio outbound de publicación (compose `video_publisher`, :8002).
PUBLISHER_URL = os.getenv("PUBLISHER_URL", "http://localhost:8002")
# El flujo real del micro incluye el poll de IG (~60s) + container/publish; el
# timeout del backend debe cubrirlo (mismo valor que agents/nodes/publish.py).
_PUBLISH_TIMEOUT = 150.0


async def _publish_to_instagram_reels(video_url: str, caption: str) -> Dict[str, Any]:
    """
    Ejecuta el flujo de publicación de 2 pasos de la Meta Graph API para Instagram Reels:
    1. POST /{ig-user-id}/media (Crear contenedor de video reel).
    2. POST /{ig-user-id}/media_publish (Publicar el contenedor).

    Legacy (compatibilidad con test_auto_publisher): el flujo productivo delega en
    el microservicio :8002, no en este helper.
    """
    logger.info(f"[Meta API] Iniciando creación de contenedor de media para Reel: {video_url[:80]}...")

    if not INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN.startswith("dev_"):
        logger.warning("[Meta API] Token de Meta Graph API simulado para desarrollo. Retornando exito simulado.")
        return {
            "status": "success",
            "media_id": f"ig_reel_container_{int(datetime.now().timestamp())}",
            "post_id": f"ig_post_{int(datetime.now().timestamp())}",
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Paso 1: Crear Contenedor Media
        container_endpoint = f"{META_GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
        container_payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
        res_container = await client.post(container_endpoint, json=container_payload)
        if res_container.status_code not in (200, 201):
            logger.error(f"[Meta API] Error creando contenedor de Reel: {res_container.text}")
            raise RuntimeError(f"Fallo en Meta Graph API contenedor: {res_container.text}")

        creation_id = res_container.json().get("id")

        # Esperar 5s a que Meta procese el video
        await asyncio.sleep(5.0)

        # Paso 2: Publicar Contenedor
        publish_endpoint = f"{META_GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
        res_publish = await client.post(publish_endpoint, json=publish_payload)
        if res_publish.status_code not in (200, 201):
            logger.error(f"[Meta API] Error en publicación final de Reel: {res_publish.text}")
            raise RuntimeError(f"Fallo en Meta Graph API media_publish: {res_publish.text}")

        post_id = res_publish.json().get("id")
        logger.info(f"[Meta API] Reel publicado exitosamente en Instagram! Post ID: {post_id}")
        return {"status": "success", "media_id": creation_id, "post_id": post_id}


def _build_credentials(tenant: Tenant) -> tuple[str, str]:
    """Credenciales tenant-first (REQ-PUB-07).

    Usa `instagram_business_account_id` / `instagram_graph_api_token_ref` del
    tenant cuando están seteados; sin ellos cae a las variables de entorno
    (tokens `dev_`/`token_` simulan en el adaptador del micro, AGENCY_ENV=dev).
    """
    user_id = tenant.instagram_business_account_id or os.getenv(
        "INSTAGRAM_ACCOUNT_ID", "dev_instagram_account_123"
    )
    token = tenant.instagram_graph_api_token_ref or os.getenv(
        "INSTAGRAM_ACCESS_TOKEN", "dev_meta_access_token_456"
    )
    return user_id, token


def _publish_idempotency_key(tenant_id: str, platform: str, edited_uri: str) -> str:
    """Stable idempotency key por (tenant, platform, video) — mismo contrato que
    `agents/nodes/publish.py` (RESILIENCE-001): un retry del mismo publish envía la
    misma key y el micro dedupea en vez de postear dos veces.
    """
    raw = f"{tenant_id}|{platform}|{edited_uri}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _process_pending_publications():
    """Busca videos 'approved' cuyo tiempo de publicación venció y los publica
    delegando al microservicio outbound (:8002)."""
    async with AsyncSessionLocal() as session:
        now_utc = datetime.now(timezone.utc)
        # REQ-PUB-04: videos 'approved' sin published_at (nunca programados) o
        # con published_at vencido. Los 'published' ya no matchean (idempotente).
        stmt = (
            select(Video, Script, Idea)
            .join(Script, Video.script_id == Script.id, isouter=True)
            .join(Idea, Script.idea_id == Idea.id, isouter=True)
            .where(
                Video.publish_approval_status == "approved",
                or_(Video.published_at.is_(None), Video.published_at <= now_utc),
            )
        )
        result = await session.execute(stmt)
        rows = result.all()

        logger.info(f"[Publisher Task] Se encontraron {len(rows)} publicaciones agendadas listas para publicar.")

        published_count = 0
        for video, script, idea in rows:
            try:
                if not video.edited_video_uri:
                    logger.warning(
                        f"[{video.tenant_id}] Video {video.id} sin edited_video_uri: "
                        "no se publica ni se fabrica una URL."
                    )
                    continue

                tenant = await session.get(Tenant, video.tenant_id)
                user_id, token = _build_credentials(tenant)
                platform = video.platform or "instagram"

                caption_text = idea.texto if idea else "Reel ViralSync AI Commercial"
                if script and script.gancho_0_5s:
                    caption_text = f"{script.gancho_0_5s}\n\n{caption_text}\n\n#ViralSync #MarketingAI"

                payload = {
                    "tenant_id": video.tenant_id,
                    "video_url": video.edited_video_uri,
                    "caption": caption_text,
                    "platform": platform,
                    "instagram_user_id": user_id,
                    "access_token": token,
                    "idempotency_key": _publish_idempotency_key(
                        video.tenant_id, platform, video.edited_video_uri
                    ),
                }

                async with httpx.AsyncClient(timeout=_PUBLISH_TIMEOUT) as client:
                    resp = await client.post(f"{PUBLISHER_URL}/publish", json=payload)
                    resp.raise_for_status()
                    result_json = resp.json()

                post_id = result_json.get("published_post_id") if isinstance(result_json, dict) else None
                if not post_id:
                    logger.error(
                        f"[{video.tenant_id}] Publisher devolvió respuesta sin published_post_id "
                        f"para video {video.id}: no se inventa un id."
                    )
                    continue

                video.instagram_post_id = post_id
                video.published_at = datetime.now(timezone.utc)
                video.publish_approval_status = "published"
                await session.commit()
                published_count += 1
                logger.info(
                    f"[{video.tenant_id}] Video {video.id} publicado en '{platform}' con Post ID '{post_id}'."
                )
            except Exception as exc:
                logger.error(f"[{video.tenant_id}] Error publicando video {video.id}: {exc}")

        return published_count


@celery_app.task(name="workers.publisher_task.auto_publish_scheduled_videos_task")
def auto_publish_scheduled_videos_task():
    """Tarea Celery periódica para verificar y auto-publicar videos agendados."""
    logger.info("[Publisher Task] Ejecutando auto_publish_scheduled_videos_task...")
    published = asyncio.run(_process_pending_publications())
    return {"status": "COMPLETED", "published_count": published}