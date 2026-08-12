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
        raise ValueError(f"Edición de video rechazada por calidad: {err_msg}")

    if render_status == "failed":
        # RELIABILITY-001 fix: a render failure must propagate honestly. The
        # fabricated default_rendered_output.mp4 URL was removed from the worker,
        # so this node never persists a lie as edited_video_uri.
        err_msg = render_res.get("message", "El renderizado de video falló.")
        logger.error(f"[{tenant_id}] Fallo honesto de renderizado en node_video_edit: {err_msg}")
        raise RuntimeError(f"Fallo en renderizado de video para tenant '{tenant_id}': {err_msg}")

    edited_uri = render_res.get("video_url")
    if not edited_uri:
        logger.error(f"[{tenant_id}] No se obtuvo video_url del microservicio de renderizado.")
        raise RuntimeError(f"Fallo en renderizado de video para tenant '{tenant_id}'. No se generó URI de salida.")

    raw_uri = state.get("raw_video_uri", f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4")

    # 3. Persistencia real (PERSIST-02): fila `videos` FK al guion. Un fallo de
    # DB se propaga (PERSIST-02-2), nunca un éxito state-only. La fila devuelta
    # por el DAO ya NO se descarta: su `id` viaja en state como `video_id` para
    # que node_publish haga el write-back (design D-A, REQ-PTT-01).
    row = await insert_video(tenant_id, script.get("id"), raw_uri, edited_uri)

    logs = state.get("logs", [])
    logs.append(f"[video_edit] Storyboard generado con {len(storyboard)} escenas cinematográficas.")
    logs.append(f"[video_edit] Video procesado exitosamente: '{edited_uri}'")

    return {
        "video_storyboard": storyboard,
        "raw_video_uri": raw_uri,
        "edited_video_uri": edited_uri,
        "video_id": row.id,
        "logs": logs,
    }