"""
publish.py

Nodo de Publicación de LangGraph (async) conectado al publisher REAL por HTTP
(design D5 / REQ-PUBLISH-02): `POST {PUBLISHER_URL}/publish` con el contrato
`PublishRequest` del microservicio (:8002 en compose).

Comportamiento honesto (REQ-API-06 / PUBLISH-02-3):
- Sin `edited_video_uri` en state → error honesto (se eliminó el default muerto
  `s3://viralsync-media-dev/...`, T-00 #3).
- Sin `ig_user_id`/`ig_access_token` → ValueError de seguridad espejo de
  adapters.py — NUNCA se fabrica un `published_post_id`.
- La simulación dev (`token_`, AGENCY_ENV=dev) vive en el micro (adapters),
  no acá: el nodo se limita a reenviar las credenciales y a devolver el id
  REAL que el publisher responde.
- `:8002` caído o respuesta sin `published_post_id` → error claro, sin simular.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import httpx
from httpx import AsyncClient

from backend.db.daos import update_video_publish, get_video_by_id

logger = logging.getLogger(__name__)

# Microservicio outbound de publicación (compose `video_publisher`, :8002).
PUBLISHER_URL = os.getenv("PUBLISHER_URL", "http://localhost:8002")

# RELIABILITY-002 fix: the publisher flow with real tokens runs the IG poll
# (12x5s = up to ~60s) plus container/publish calls, so worst case is ~90s+.
# The backend client timeout MUST cover that legitimate duration; 15s used to
# abort healthy publishes and force frontend retries that duplicated posting.
_PUBLISH_TIMEOUT = 150.0


def _publish_idempotency_key(tenant_id: str, platform: str, edited_uri: str) -> str:
    """Stable idempotency key for one logical publication (RESILIENCE-001).

    Derived from tenant+platform+video identity so a backend retry or a client
    double-submit of the SAME publish sends the same key and the publisher can
    dedupe instead of posting the video twice.
    """
    import hashlib

    raw = f"{tenant_id}|{platform}|{edited_uri}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def node_publish(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que efectúa la publicación final vía el publisher HTTP real (:8002)."""
    tenant_id = state.get("tenant_id", "default_tenant")
    edited_uri = state.get("edited_video_uri")

    # FASE-3 (elegir variante): si el resume trajo `video_id` (la variante que el
    # usuario aprobó), la URI a publicar es la de ESA fila `videos` — no
    # necesariamente la "principal" del state. Si la fila no existe o el lookup
    # falla, se cae al comportamiento actual (URI del state) sin romper el publish;
    # el write-back posterior (REQ-PTT-01) escribe igual sobre el video_id del state.
    video_id = state.get("video_id")
    if video_id:
        try:
            video_row = await get_video_by_id(tenant_id, video_id)
        except Exception as exc:  # noqa: BLE001 - el lookup no debe abortar el publish
            logger.warning(
                f"[{tenant_id}] get_video_by_id falló para video_id {video_id} "
                f"({exc}); usando edited_video_uri del state"
            )
            video_row = None
        if video_row and video_row.edited_video_uri:
            edited_uri = video_row.edited_video_uri

    if not edited_uri:
        raise ValueError(
            f"[{tenant_id}] edited_video_uri ausente en state: no hay video "
            "renderizado para publicar (T-00 #3, sin default s3://)."
        )

    script = state.get("script", {})
    caption = f"{script.get('gancho_0_5s', '')}\n\n{script.get('cta_50_60s', '')}"
    platform = state.get("target_platform", "instagram")

    # Credenciales OAuth desde el estado del grafo (request-scoped, REQ-PUBLISH-01):
    # vienen del endpoint /graph/run → frontend (sesión del usuario). Nunca se
    # persisten en el servidor.
    user_id = state.get("ig_user_id")
    token = state.get("ig_access_token")
    if platform == "tiktok":
        token = state.get("tiktok_access_token")
    elif platform == "youtube_shorts":
        token = state.get("youtube_access_token")

    if not user_id or not token:
        raise ValueError(
            f"[{tenant_id}] Fallo de Seguridad: Token o User ID de Instagram "
            "ausente. No se permite fallback global para evitar fugas entre tenants."
        )

    payload = {
        "tenant_id": tenant_id,
        "video_url": edited_uri,
        "caption": caption,
        "platform": platform,
        "instagram_user_id": user_id,
        "access_token": token,
        # RESILIENCE-001: idempotency key so a retry of the same publish does
        # not create a duplicate post. Stable for (tenant, platform, video).
        "idempotency_key": _publish_idempotency_key(tenant_id, platform, edited_uri),
    }

    try:
        async with AsyncClient(timeout=_PUBLISH_TIMEOUT) as client:
            resp = await client.post(f"{PUBLISHER_URL}/publish", json=payload)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"[{tenant_id}] Publisher no disponible o falló ({PUBLISHER_URL}): {exc}"
        ) from exc

    post_id = result.get("published_post_id") if isinstance(result, dict) else None
    if not post_id:
        raise RuntimeError(
            f"[{tenant_id}] Publisher devolvió respuesta sin published_post_id: "
            "no se inventa un id."
        )

    logger.info(f"[{tenant_id}] Video publicado en '{platform}' con Post ID '{post_id}'")

    # REQ-PTT-01 / D-F: write-back atómico. Tras POST 2xx + post_id REAL, la fila
    # `videos` (identificada por `video_id` en state) guarda dónde se publicó
    # (instagram_post_id + published_at) en UN solo UPDATE. Sin `video_id` en
    # state (replay/resume) → skip sin crash y sin fabricar un id (PTT-01-3); si
    # el publisher raise, nunca llegamos acá → no write parcial (PTT-01-2).
    video_id = state.get("video_id")
    if video_id:
        updated = await update_video_publish(
            tenant_id, video_id, post_id, datetime.now(timezone.utc)
        )
        if not updated:
            logger.error(
                f"[{tenant_id}] Write-back fallido: update_video_publish afectó 0 filas "
                f"para video_id {video_id} (tenant_id mismatch o id inexistente)"
            )

    logs = state.get("logs", [])
    if video_id and not updated:
        logs.append(
            f"[publish] ADVERTENCIA: Write-back fallido en BD para video_id '{video_id}' (0 filas actualizadas)"
        )
    logs.append(f"[publish] Video publicado en {platform.capitalize()} con Post ID '{post_id}'")

    return {
        "published_post_id": post_id,
        "logs": logs,
    }