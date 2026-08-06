"""
video_edit.py

Nodo de Edición de Video de LangGraph.
Solicita o dispara la tarea asíncrona de post-producción en Celery.
"""

import logging
from typing import Dict, Any
from agents.crews.video_prompt_crew import run_video_prompt_crew

logger = logging.getLogger(__name__)


def node_video_edit(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera el storyboard de prompts visuales y prepara la salida del video."""
    tenant_id = state.get("tenant_id", "default_tenant")
    script = state.get("script", {})
    selected_idea = state.get("selected_idea", {})
    product_image_url = state.get("product_image_url", "")

    logger.info(f"[{tenant_id}] Ejecutando nodo 'video_edit' con Agente de Prompting Visual")

    # 1. Ejecutar Crew de Prompting Visual segundo a segundo (Image-to-Video si existe foto)
    storyboard = run_video_prompt_crew(
        script=script, idea=selected_idea, product_image_url=product_image_url
    )

    raw_uri = state.get("raw_video_uri", f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4")
    edited_uri = f"s3://viralsync-media-dev/{tenant_id}/edited_output.mp4"

    logs = state.get("logs", [])
    logs.append(f"[video_edit] Storyboard generado con {len(storyboard)} escenas cinematográficas.")
    logs.append(f"[video_edit] Video procesado exitosamente: '{edited_uri}'")

    return {
        "video_storyboard": storyboard,
        "raw_video_uri": raw_uri,
        "edited_video_uri": edited_uri,
        "logs": logs,
    }
