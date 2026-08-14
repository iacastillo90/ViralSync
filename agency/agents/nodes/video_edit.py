"""
video_edit.py

Nodo de Edición de Video de LangGraph.
Solicita o dispara la tarea asíncrona de post-producción en Celery y persiste la
fila `videos` vía DAO (design D3): `insert_video` escribe la fila con FK al
guion, capturando las URIs crudo/editado y `publish_approval_status='pending'`
(REQ-PERSIST-02).
"""

import logging
from typing import Dict, Any
from agents.crews.video_prompt_crew import run_video_prompt_crew
from workers.video_edit_task import trigger_video_render
from backend.db.daos import insert_video
from backend.storage.minio_client import presign_public_url

logger = logging.getLogger(__name__)


async def node_video_edit(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera el storyboard de prompts visuales y efectúa el renderizado real del video."""
    tenant_id = state.get("tenant_id", "default_tenant")
    script = state.get("script", {})
    selected_idea = state.get("selected_idea", {})
    product_image_url = state.get("product_image_url", "")

    # PERSIST-05-1 / D-5 (SH-05-3/4) + RISK-001 defense-in-depth: si el state
    # trae la key ESTABLE del objeto DENTRO del prefijo del tenant, re-firmar en
    # CADA lectura (presigned_get_object) — la URL almacenada expiró. Filas
    # legacy sin key (NULL) o keys FUERA del prefijo (cross-tenant, RISK-001)
    # → fallback a la URL guardada tal cual (SH-05-4): nunca se re-firma ni se
    # filtra una URL presignada de un objeto ajeno al tenant.
    product_object_key = state.get("product_object_key")
    if product_object_key and product_object_key.startswith(f"{tenant_id}/"):
        product_image_url = presign_public_url(product_object_key)

    logger.info(f"[{tenant_id}] Ejecutando nodo 'video_edit' con Agente de Prompting Visual")

    # Notificar inicio de renderizado vía SSE
    try:
        from backend.sse_manager import sse_manager
        sse_manager.publish_event(tenant_id, "video_render_started", {
            "script_id": script.get("id"),
            "title": (script.get("gancho_0_5s") or "Reel 9:16")[:50],
        })
    except Exception as sse_err:
        logger.debug(f"SSE notify bypass: {sse_err}")

    # 1. Ejecutar Crew de Prompting Visual segundo a segundo (Image-to-Video si existe foto)
    storyboard = await run_video_prompt_crew(
        script=script, idea=selected_idea, product_image_url=product_image_url
    )

    # 2. Invocar renderizado real vía microservicio / Celery worker
    render_res = trigger_video_render(
        tenant_id=tenant_id,
        script=script,
        idea=selected_idea,
        storyboard=storyboard,
        product_image_url=product_image_url,
    )
    render_status = render_res.get("status")

    if render_status == "rejected_quality":
        err_msg = render_res.get("message", "El guion no superó la calidad RUM requerida.")
        logger.error(f"[{tenant_id}] Fallo explícito en node_video_edit: {err_msg}")
        try:
            from backend.sse_manager import sse_manager
            sse_manager.publish_event(tenant_id, "video_render_failed", {"script_id": script.get("id"), "error": err_msg})
        except Exception:
            pass
        raise ValueError(f"Edición de video rechazada por calidad: {err_msg}")

    if render_status == "failed":
        err_msg = render_res.get("message", "El renderizado de video falló.")
        logger.error(f"[{tenant_id}] Fallo honesto de renderizado en node_video_edit: {err_msg}")
        try:
            from backend.sse_manager import sse_manager
            sse_manager.publish_event(tenant_id, "video_render_failed", {"script_id": script.get("id"), "error": err_msg})
        except Exception:
            pass
        raise RuntimeError(f"Fallo en renderizado de video para tenant '{tenant_id}': {err_msg}")

    variants = render_res.get("variants")
    if not variants:
        # Compatibilidad con retornos legacy (mocks/tests) que no exponen
        # `variants`: tratar la variante principal como una única variante.
        # El worker nuevo siempre envía `variants`.
        variant_url = render_res.get("video_url")
        if variant_url:
            variants = [{"provider": render_res.get("provider", "local"), "video_url": variant_url}]
        else:
            logger.error(f"[{tenant_id}] Render completado sin variantes para persistir.")
            raise RuntimeError(f"Render completado sin variantes para persistir para tenant '{tenant_id}'.")

    raw_uri = state.get("raw_video_uri", f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4")

    # 3. Persistencia real (PERSIST-02): UNA fila `videos` POR variante generada
    # (json2video + local), distinguidas por `provider` (migración 007). El
    # state del grafo sigue exponiendo UNA sola variante principal
    # (`edited_video_uri`/`video_id`): la json2video si existe, si no la local,
    # para no romper el contrato con node_publish. Un fallo de DB se propaga
    # (PERSIST-02-2), nunca un éxito state-only.
    primary_provider = render_res.get("provider", "local")
    primary_uri = render_res.get("video_url", "")
    video_id = None
    for variant in variants:
        url = variant.get("video_url")
        provider = variant.get("provider", "local")
        if not url:
            continue
        row = await insert_video(tenant_id, script.get("id"), raw_uri, url, provider=provider)
        if provider == primary_provider:
            video_id = row.id
        logger.info(f"[{tenant_id}] Variante '{provider}' persistida en videos (video_id={row.id})")

    logs = state.get("logs", [])
    logs.append(f"[video_edit] Storyboard generado con {len(storyboard)} escenas cinematográficas.")
    logs.append(f"[video_edit] Video procesado exitosamente: '{primary_uri}' ({len(variants)} variante(s) persistida(s))")

    # Emitir evento SSE de renderizado completado
    try:
        from backend.sse_manager import sse_manager
        sse_manager.publish_event(tenant_id, "video_render_completed", {
            "script_id": script.get("id"),
            "video_id": video_id,
            "video_url": primary_uri,
            "provider": primary_provider,
        })
    except Exception as sse_err:
        logger.debug(f"SSE completed notify bypass: {sse_err}")

    return {
        "video_storyboard": storyboard,
        "raw_video_uri": raw_uri,
        "edited_video_uri": primary_uri,
        "video_id": video_id,
        "logs": logs,
    }