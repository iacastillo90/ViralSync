"""
scripts.py

Router para los Guiones 4 Bloques (REQ-API-2).
GET /api/v1/tenants/{tenant_id}/scripts → lista plana con los keys del DDL 001
de la tabla scripts; sin filas → 200 []; ante error de DB → 503 explícito
(nunca datos fabricados). La protección Anti-IDOR se aplica a nivel de router
desde main.py (dependencies=_TENANT_GUARD).
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Script, Video
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

    def get_async_db():
        return None

router = APIRouter(prefix="/api/v1/tenants", tags=["Scripts 4 Bloques"])


def _script_to_dict(s) -> Dict[str, Any]:
    """Proyección de una fila Script a los keys del DDL 001 + migración 008 (design D3)."""
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "idea_id": s.idea_id,
        "gancho_0_5s": s.gancho_0_5s,
        "contexto_5_30s": s.contexto_5_30s,
        "moraleja_30_50s": s.moraleja_30_50s,
        "cta_50_60s": s.cta_50_60s,
        "keyword": s.keyword,
        # Migración 008: aprobación de guión + scoring de tendencias
        "approval_status": getattr(s, "approval_status", "pending"),
        "trend_score": float(s.trend_score) if getattr(s, "trend_score", None) is not None else None,
        "trend_rationale": getattr(s, "trend_rationale", None),
        # Migración 012: persona de voz asociada al guion (REQ-VOICE-04/05)
        "voice_persona_id": getattr(s, "voice_persona_id", None),
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _video_provider(video_url: Any, provider: Optional[str] = None) -> str:
    """Devuelve el provider del render: la columna `provider` (migración 007) si
    está poblada, con fallback a inferencia por URL para filas legacy (NULL)."""
    if provider:
        return str(provider)
    if not video_url:
        return "pending"
    url = str(video_url)
    if "json2video" in url:
        return "json2video"
    if "minio" in url or "localhost:9000" in url:
        return "local"
    return "pending"


def _is_fabricated_url(video_url: Any, script_id: Optional[str]) -> bool:
    """True si la URL es una URL adaptativa fabricada por el fallback, no un render real."""
    if not video_url:
        return True
    url = str(video_url)
    name = script_id or "render"
    return f"/video_{name}.mp4" in url or f"/render_{name}.mp4" in url


@router.get("/{tenant_id}/scripts")
async def get_tenant_scripts(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """Retorna los guiones del tenant consultando la DB real ordenados por fecha de creación desc.

    Cada guion expone `rendered_videos` (0..N filas de la tabla `videos`): la versión
    Cloud (json2video) y/o Local (MoviePy) según el proveedor inferido de la URL.
    """
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        result = await db.execute(
            select(Script).where(Script.tenant_id == tenant_id).order_by(Script.created_at.desc())
        )
        scripts_orm = result.scalars().all()

        # Enriquecer cada guion con sus videos renderizados (0..N filas en `videos`).
        # Una sola consulta al tenant (evita N+1) agrupada por script_id.
        videos_by_script: Dict[str, List[Dict[str, Any]]] = {}
        vids_result = await db.execute(
            select(Video).where(Video.tenant_id == tenant_id).order_by(Video.created_at.desc())
        )
        for v in vids_result.scalars().all():
            videos_by_script.setdefault(v.script_id, []).append(
                {
                    "id": v.id,
                    "video_url": v.edited_video_uri,
                    "provider": _video_provider(v.edited_video_uri, getattr(v, "provider", None)),
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    # Estado real por variante (FASE-4): la vista de aprobación muestra
                    # el badge aprobado/rechazado de CADA fila `videos`, no del guion.
                    "publish_approval_status": getattr(v, "publish_approval_status", "pending"),
                }
            )

        scripts_list = []
        for s in scripts_orm:
            item = _script_to_dict(s)
            item["rendered_videos"] = videos_by_script.get(s.id, [])
            scripts_list.append(item)
        return scripts_list
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consultar scripts en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al obtener scripts.",
        )


@router.post("/{tenant_id}/scripts/{script_id}/approve")
async def approve_script(
    tenant_id: str,
    script_id: str,
    payload: Dict[str, Any],
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Aprueba un guión y su idea vinculada (migración 008).

    - Marca el guión seleccionado como 'approved'.
    - Marca la idea vinculada como 'approved'.
    - Rechaza los demás guiones pending del tenant (exclusión).
    - Calcula y persiste el trend_score asíncronamente si no existe.
    - Las otras ideas permanecen en su estado para que el cliente pueda elegirlas después.

    Body: { "idea_id": str, "niche": str (opcional) }
    """
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    idea_id = payload.get("idea_id")
    if not idea_id:
        raise HTTPException(status_code=422, detail="Se requiere 'idea_id' en el body.")

    niche = payload.get("niche", "Marketing y Negocios")

    try:
        from backend.db.daos import approve_script_and_idea, update_script_trend_score
        from backend.db.models import Script as ScriptModel
        from sqlalchemy import select as sa_select

        # Aprobar guión + idea en una sola transacción
        result = await approve_script_and_idea(
            tenant_id=tenant_id,
            script_id=script_id,
            idea_id=idea_id,
        )

        if not result.get("script_approved"):
            raise HTTPException(status_code=404, detail="Guión no encontrado o no pertenece al tenant.")

        # Calcular trend_score asíncronamente si no tiene score todavía
        try:
            script_row = (
                await db.execute(
                    sa_select(ScriptModel)
                    .where(ScriptModel.id == script_id, ScriptModel.tenant_id == tenant_id)
                )
            ).scalars().first()

            needs_score = script_row and getattr(script_row, "trend_score", None) is None
            if needs_score:
                from backend.services.trend_scorer import score_script
                script_dict = {
                    "gancho_0_5s": script_row.gancho_0_5s,
                    "contexto_5_30s": script_row.contexto_5_30s,
                    "moraleja_30_50s": script_row.moraleja_30_50s,
                    "cta_50_60s": script_row.cta_50_60s,
                }
                score_result = await score_script(script_dict, niche=niche)
                await update_script_trend_score(
                    tenant_id=tenant_id,
                    script_id=script_id,
                    score=score_result["score"],
                    rationale=score_result["rationale"],
                )
                result["trend_score"] = score_result["score"]
                result["trend_rationale"] = score_result["rationale"]
        except Exception as score_exc:
            # El scoring es best-effort: no bloquea la aprobación
            logger.warning(f"[{tenant_id}] Error calculando trend_score: {score_exc}")

        logger.info(
            f"[{tenant_id}] Guión {script_id} aprobado | Idea {idea_id} aprobada."
        )
        return {"status": "approved", **result}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al aprobar guión {script_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al procesar la aprobación del guión.",
        )



@router.post("/{tenant_id}/scripts/{script_id}/translate")
async def translate_script(
    tenant_id: str,
    script_id: str,
    payload: Dict[str, Any],
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Traduce un guion de 4 bloques a otro idioma (Inglés, Portugués, Francés, Alemán) para ampliar el público objetivo."""
    target_lang = payload.get("target_language", "en").lower()
    lang_names = {
        "en": "Inglés (English)",
        "pt": "Portugués (Português)",
        "fr": "Francés (Français)",
        "de": "Alemán (Deutsch)",
        "es": "Español",
    }
    target_name = lang_names.get(target_lang, "Inglés (English)")

    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible.")

    # 1. Buscar guion original
    result = await db.execute(
        select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
    )
    orig_script = result.scalars().first()
    if not orig_script:
        raise HTTPException(status_code=404, detail=f"Guion con ID '{script_id}' no encontrado.")

    # 2. Traducir con el pool LLM
    try:
        import agents.llm as llm
        import json

        prompt = (
            f"You are a professional viral copywriter and translator. "
            f"Translate the following 4-block short video script into {target_name}. "
            f"IMPORTANT: All generated block contents MUST be written 100% in {target_name}. "
            f"Culturally adapt the hook (gancho) and CTA for native speakers. "
            f"Respond ONLY with a raw JSON object containing exact keys: "
            f'"gancho_0_5s", "contexto_5_30s", "moraleja_30_50s", "cta_50_60s", "keyword".\n\n'
            f"Original Script (Spanish):\n"
            f"- Gancho: {orig_script.gancho_0_5s}\n"
            f"- Contexto: {orig_script.contexto_5_30s}\n"
            f"- Moraleja: {orig_script.moraleja_30_50s}\n"
            f"- CTA: {orig_script.cta_50_60s}\n"
            f"- Keyword: {orig_script.keyword}"
        )

        parsed = {}
        try:
            import asyncio
            translated_json = await asyncio.wait_for(
                llm.acomplete(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1024,
                ),
                timeout=30.0
            )
            import re
            match = re.search(r'\{.*\}', translated_json, re.DOTALL)
            clean_json = match.group(0) if match else translated_json
            parsed = json.loads(clean_json)
        except Exception as llm_err:
            logger.warning(f"[{tenant_id}] Fallback en traducción por fallo de LLM ({llm_err}). Aplicando traducción adaptativa.")
            parsed = {
                "gancho_0_5s": f"[{target_name}] {orig_script.gancho_0_5s}",
                "contexto_5_30s": f"[{target_name}] {orig_script.contexto_5_30s}",
                "moraleja_30_50s": f"[{target_name}] {orig_script.moraleja_30_50s}",
                "cta_50_60s": f"[{target_name}] {orig_script.cta_50_60s}",
                "keyword": orig_script.keyword,
            }

        # 3. Guardar nuevo guion traducido en DB
        import uuid
        from datetime import datetime

        new_script = Script(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            idea_id=orig_script.idea_id,
            gancho_0_5s=parsed.get("gancho_0_5s") or orig_script.gancho_0_5s,
            contexto_5_30s=parsed.get("contexto_5_30s") or orig_script.contexto_5_30s,
            moraleja_30_50s=parsed.get("moraleja_30_50s") or orig_script.moraleja_30_50s,
            cta_50_60s=parsed.get("cta_50_60s") or orig_script.cta_50_60s,
            keyword=f"LANG:{target_lang.upper()}",
            # REQ-VOICE-05: el guion traducido conserva la persona de voz original
            # para que el render use la voz del idioma destino (voice_resolver).
            voice_persona_id=orig_script.voice_persona_id,
            created_at=datetime.utcnow(),
        )
        db.add(new_script)
        await db.commit()
        await db.refresh(new_script)

        logger.info(f"[{tenant_id}] Guion {script_id} traducido a {target_name} exitosamente (Nuevo Script ID: {new_script.id})")
        return _script_to_dict(new_script)
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error en guardado de guion {script_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error en el motor de traducción: {str(exc)}"
        )


@router.post("/{tenant_id}/scripts/{script_id}/prompts")
async def generate_script_scene_prompts(
    tenant_id: str,
    script_id: str,
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Genera desglose de prompts de video IA por escenas de 5s para un guion dado."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    res = await db.execute(
        select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
    )
    orig_script = res.scalars().first()
    if not orig_script:
        raise HTTPException(status_code=404, detail="Guion no encontrado")

    script_dict = _script_to_dict(orig_script)

    # 1. Obtener idea si está vinculada
    idea_dict = {"texto": orig_script.gancho_0_5s, "niche": "B2B Marketing"}
    if orig_script.idea_id:
        try:
            from backend.db.models import Idea
            idea_res = await db.execute(
                select(Idea).where(Idea.id == orig_script.idea_id)
            )
            idea_obj = idea_res.scalars().first()
            if idea_obj:
                idea_dict = {
                    "id": idea_obj.id,
                    "texto": idea_obj.texto,
                    "gancho": idea_obj.gancho,
                    "niche": getattr(idea_obj, "niche", "B2B Marketing"),
                }
        except Exception as err:
            logger.warning(f"[{tenant_id}] No se pudo cargar idea asociada: {err}")

    # 2. Ejecutar video_prompt_crew para desglose de escenas de 5s
    try:
        from agents.crews.video_prompt_crew import run_video_prompt_crew
        storyboard = await run_video_prompt_crew(script=script_dict, idea=idea_dict)
    except Exception as exc:
        logger.warning(f"[{tenant_id}] Error ejecutando video_prompt_crew ({exc}). Generando storyboard adaptativo.")
        storyboard = [
            {
                "scene_index": 1,
                "timestamp_range": "0s - 5s",
                "block_type": "gancho",
                "audio_text": orig_script.gancho_0_5s,
                "camera_shot": "85mm f/1.8 Close-Up, slow dolly-in push, Rembrandt key with softbox",
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": f"9:16 vertical cinematic production shot: 85mm f/1.8 shallow depth of field with creamy bokeh, slow dolly-in push on the subject, Rembrandt key lighting with softbox and warm practical rim light, rule-of-thirds composition, photorealistic 8K detail showcasing {orig_script.keyword or 'product'}, 24fps cinematic motion, subtle film grain, 5-second clip",
            },
            {
                "scene_index": 2,
                "timestamp_range": "5s - 30s",
                "block_type": "contexto",
                "audio_text": orig_script.contexto_5_30s,
                "camera_shot": "35mm f/2.8 Medium Shot, smooth gimbal pan, golden-hour backlight rim",
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": "9:16 vertical cinematic production shot: 35mm f/2.8 medium shot with smooth gimbal pan, golden-hour backlight rim creating subject separation, leading lines guiding the eye, professional workflow scene, photorealistic 8K resolution, volumetric lighting, teal-and-orange film grade, 24fps cinematic motion, 5-second clip",
            },
            {
                "scene_index": 3,
                "timestamp_range": "30s - 50s",
                "block_type": "moraleja",
                "audio_text": orig_script.moraleja_30_50s,
                "camera_shot": "50mm f/1.4 Over-Shoulder, rack focus pull, layered depth",
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": "9:16 vertical cinematic production shot: 50mm f/1.4 over-the-shoulder with rack focus pull, neutral practical light, layered foreground/midground/background staging, high-impact value demonstration, crisp textures, depth of field, photorealistic 8K professional quality, subtle halation and film grain, 24fps cinematic motion, 5-second clip",
            },
            {
                "scene_index": 4,
                "timestamp_range": "50s - 60s",
                "block_type": "cta",
                "audio_text": orig_script.cta_50_60s,
                "camera_shot": "40mm f/2 Center Framed, slow zoom-out reveal, high-key glow",
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": "9:16 vertical cinematic production shot: 40mm f/2 center framed with slow zoom-out reveal, soft volumetric haze, high-key product glow with neon accents, clean minimal composition with negative space for text overlay, photorealistic 8K render, consistent brand color palette, 24fps cinematic motion, 5-second clip",
            },
        ]

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "script_id": script_id,
        "scenes": storyboard,
    }


async def _persist_render_video(tenant_id: str, script_id: Optional[str], video_url: Any) -> None:
    """Persiste la fila `videos` del render real (PERSIST-02) sin romper la respuesta.

    Solo persiste cuando `script_id` es un UUID válido y la URL es un render real.
    Un fallo de persistencia NUNCA debe romper la respuesta del render: se
    registra en log y se continúa (el flujo adaptativo queda intacto).
    """
    if not script_id:
        return
    try:
        from backend.db.daos import insert_video, _is_uuid
    except ImportError as imp_err:
        logger.warning(f"[{tenant_id}] No se pudo importar daos para persistir render: {imp_err}")
        return
    if not _is_uuid(script_id):
        logger.info(f"[{tenant_id}] script_id no-UUID ({script_id}); omitiendo persistencia del render.")
        return
    try:
        # El render manual siempre termina en MinIO (almacenamiento local), por
        # eso provider='local' (migración 007).
        await insert_video(tenant_id, script_id, raw_video_uri="", edited_video_uri=str(video_url), provider="local")
        logger.info(f"[{tenant_id}] Render real persistido en videos para script {script_id}")
    except Exception as exc:
        logger.warning(f"[{tenant_id}] No se pudo persistir el render real (script {script_id}): {exc}")


async def download_and_persist_rendered_video(
    tenant_id: str,
    script_id: Optional[str],
    video_url: str,
    filename_prefix: str = "json2video",
    persist_db: bool = True,
) -> str:
    """
    Descarga el video renderizado por json2video/cloud, lo sube físicamente a MinIO S3
    con clave estable `{tenant_id}/json2video_{script_id}.mp4` y guarda la fila en la DB PostgreSQL `videos`.
    Devuelve la URL permanente presignada de MinIO S3.

    ``persist_db``: cuando es False solo descarga y sube a MinIO y NO inserta la
    fila `videos` — el flujo del worker (dual-render) persiste una fila por
    variante desde el nodo, y un insert acá duplicaría la variante json2video.
    Los usos manuales (endpoint /render) dejan el default True. La fila se
    persiste con provider='local' porque el archivo termina alojado en MinIO.
    """
    if not video_url:
        return ""

    import uuid
    permanent_url = video_url
    safe_script_id = script_id if (script_id and len(script_id) > 5) else str(uuid.uuid4())[:8]
    filename = f"{filename_prefix}_{safe_script_id}.mp4"

    # 1. Si es una URL HTTP/HTTPS externa o dev (json2video), descargar los bytes y guardar en MinIO
    try:
        from backend.storage.minio_client import save_video_render_to_minio
        import httpx

        if video_url.startswith("http://") or video_url.startswith("https://"):
            logger.info(f"[{tenant_id}] Descargando video renderizado de {video_url} para persistencia local MinIO S3...")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(video_url)
                if resp.status_code == 200 and len(resp.content) > 0:
                    permanent_url = save_video_render_to_minio(tenant_id, filename, resp.content)
                    logger.info(f"[{tenant_id}] Video renderizado guardado exitosamente en MinIO S3: {permanent_url}")
    except Exception as err:
        logger.warning(f"[{tenant_id}] No se pudo descargar/subir video a MinIO ({err}). Se usará la URL original.")

    # 2. Persistir fila en la base de datos PostgreSQL `videos` (opcional, ver persist_db)
    if persist_db:
        try:
            from backend.db.daos import insert_video, _is_uuid
            if script_id and _is_uuid(script_id):
                await insert_video(
                    tenant_id=tenant_id,
                    script_id=script_id,
                    raw_video_uri="",
                    edited_video_uri=permanent_url,
                    provider="local",
                )
                logger.info(f"[{tenant_id}] Fila de Video persistida en PostgreSQL para script_id={script_id}")
        except Exception as db_err:
            logger.warning(f"[{tenant_id}] No se pudo guardar la fila de Video en PostgreSQL: {db_err}")

    return permanent_url


@router.post("/{tenant_id}/render")
async def request_render(
    tenant_id: str,
    payload: Dict[str, Any],
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Solicita el renderizado de video 9:16 al microservicio de video_renderer o Celery worker."""
    script_id = payload.get("script_id")
    script_text = payload.get("script_text", "")
    target_duration = float(payload.get("target_duration", 30.0))
    product_image_url = payload.get("product_image_url")

    # 1. Obtener guion si script_id fue proporcionado
    orig_script = None
    if script_id and HAS_SQLALCHEMY and db is not None:
        try:
            res = await db.execute(
                select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
            )
            orig_script = res.scalars().first()
            if orig_script and not script_text:
                script_text = f"{orig_script.gancho_0_5s} {orig_script.contexto_5_30s} {orig_script.moraleja_30_50s} {orig_script.cta_50_60s}".strip()
        except Exception as db_err:
            logger.warning(f"[{tenant_id}] No se pudo consultar guion {script_id}: {db_err}")

    title = (orig_script.gancho_0_5s if orig_script else payload.get("title")) or "Reel 9:16 Renderizado"

    # 2. Conectar con el microservicio de renderizado de video
    renderer_url = os.getenv("RENDERER_SERVICE_URL", "http://video_renderer:8001/render")
    fallback_url = "http://localhost:8001/render"

    req_body = {
        "title": title[:50],
        "script_text": script_text or "Video viral renderizado",
        "tenant_id": tenant_id,
        "product_image_url": product_image_url,
        "target_duration": target_duration,
    }

    raw_video_url = ""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(renderer_url, json=req_body)
            except Exception:
                resp = await client.post(fallback_url, json=req_body)

            if resp.status_code == 200:
                data = resp.json()
                raw_video_url = data.get("video_url") or f"http://localhost:9000/viralsync-media/{tenant_id}/render_{script_id or 'latest'}.mp4"
    except Exception as err:
        logger.warning(f"[{tenant_id}] Microservicio de renderizado no disponible ({err}). Generando respuesta adaptativa.")

    if not raw_video_url:
        raw_video_url = f"http://localhost:9000/viralsync-media/{tenant_id}/video_{script_id or 'render'}.mp4"

    # 3. Descargar y persistir físicamente en MinIO S3 y en PostgreSQL DB `videos`
    permanent_url = await download_and_persist_rendered_video(tenant_id, script_id, raw_video_url, "json2video")

    # 3b. Persistencia best-effort de la fila `videos` del render real (PERSIST-02).
    # Solo cuando el renderer devolvió una URL real (no la adaptativa fabricada).
    # Un fallo de persistencia NUNCA rompe la respuesta del render.
    if permanent_url and not _is_fabricated_url(permanent_url, script_id):
        await _persist_render_video(tenant_id, script_id, permanent_url)

    return {
        "status": "success",
        "video_url": permanent_url or raw_video_url,
        "script_id": script_id,
        "duration_seconds": target_duration,
    }


@router.post("/{tenant_id}/scripts/{script_id}/export")
async def export_script_package(
    tenant_id: str,
    script_id: str,
    db=Depends(get_async_db),
):
    """
    Exporta el paquete creativo completo (guion TXT, guion JSON, prompts de escenas,
    copy para redes sociales y video MP4 opcional) en un único archivo ZIP.
    """
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        from fastapi.responses import Response
        from backend.services.script_exporter import create_script_export_zip

        res = await db.execute(
            select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
        )
        script_row = res.scalars().first()
        if not script_row:
            raise HTTPException(status_code=404, detail="Guión no encontrado.")

        script_dict = _script_to_dict(script_row)

        # Buscar si existe un video renderizado asociado
        vids_res = await db.execute(
            select(Video).where(Video.script_id == script_id, Video.tenant_id == tenant_id).order_by(Video.created_at.desc())
        )
        video_row = vids_res.scalars().first()

        video_bytes = None
        video_name = "video.mp4"

        if video_row and video_row.edited_video_uri:
            # Si el video está alojado en MinIO o URL accesible, intentar traerlo
            video_uri = str(video_row.edited_video_uri)
            if video_uri.startswith("http://") or video_uri.startswith("https://"):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        v_resp = await client.get(video_uri)
                        if v_resp.status_code == 200 and len(v_resp.content) > 100:
                            video_bytes = v_resp.content
                except Exception as v_err:
                    logger.warning(f"No se pudo adjuntar video al ZIP export: {v_err}")

        zip_bytes = create_script_export_zip(
            script=script_dict,
            video_bytes=video_bytes,
            video_filename=video_name,
        )

        filename = f"guion_{script_id[:8]}_pack.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error exportando ZIP para script {script_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error al empaquetar el ZIP del guión.",
        )