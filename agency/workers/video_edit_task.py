"""
video_edit_task.py

Tarea Celery asíncrona para la post-producción de video:
- Recorte de silencios de audio muertos.
- Generación de subtítulos dinámicos con Whisper.
- Inserción de B-roll y SFX de interrupción de patrón.
"""

import logging
from typing import Dict, Any, List, Optional
from workers.celery_app import celery_app
from agents.mcp_servers.video_gen_client import (
    VideoGenerationClient,
    ShotstackClient,
    generate_storyboard_videos,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.video_edit_task.process_video_postproduction")
def process_video_postproduction(
    tenant_id: str,
    raw_video_uri: str,
    script: Dict[str, Any],
    storyboard: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Procesa las escenas del storyboard con APIs de generación (Fal.ai, Shotstack, Veo)
    y compila el archivo MP4 final en la nube.
    
    :param tenant_id: ID del tenant.
    :param raw_video_uri: Ruta S3/R2 del video crudo o base.
    :param script: Guion de 4 bloques con palabra clave CTA.
    :param storyboard: Lista de escenas con prompts cinematográficos desglosados.
    :return: Diccionario con la URI del video editado MP4 y plantilla de renderizado.
    """
    logger.info(f"[{tenant_id}] Iniciando pipeline de renderizado y producción de video MP4...")

    # 1. Si no viene storyboard, estructurar escenas por defecto desde el guion
    if not storyboard:
        storyboard = [
            {"scene_index": 1, "audio_text": script.get("gancho_0_5s", "Gancho"), "visual_prompt": "Cinematic close-up"},
            {"scene_index": 2, "audio_text": script.get("contexto_5_30s", "Contexto"), "visual_prompt": "Montage video"},
            {"scene_index": 3, "audio_text": script.get("moraleja_30_50s", "Moraleja"), "visual_prompt": "Portrait video"},
            {"scene_index": 4, "audio_text": script.get("cta_50_60s", "CTA"), "visual_prompt": "Text overlay"},
        ]

    # 2. Generar clips individuales por escena vía API (Fal.ai / Shotstack / Veo)
    logger.info(f"[{tenant_id}] Generando clips para {len(storyboard)} escenas del Storyboard...")
    generated_scenes = generate_storyboard_videos(storyboard=storyboard, tenant_id=tenant_id)

    # 3. Ensamblar linea de tiempo 9:16 y subtítulos con Shotstack API
    shotstack = ShotstackClient()
    edit_template = shotstack.create_edit_template(
        scenes=generated_scenes,
        audio_url=raw_video_uri if raw_video_uri.endswith(".mp3") else "",
        tenant_id=tenant_id,
    )

    # 4. Enviar renderizado final y obtener URI del archivo MP4
    edited_video_uri = shotstack.submit_render(edit_template, tenant_id=tenant_id)

    logger.info(f"[{tenant_id}] Video MP4 final producido exitosamente: {edited_video_uri}")

    return {
        "tenant_id": tenant_id,
        "raw_video_uri": raw_video_uri,
        "edited_video_uri": edited_video_uri,
        "generated_scenes": generated_scenes,
        "shotstack_template": edit_template,
        "status": "completed",
    }
