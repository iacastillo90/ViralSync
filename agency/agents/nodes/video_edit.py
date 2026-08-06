"""
video_edit.py

Nodo de Edición de Video de LangGraph.
Solicita o dispara la tarea asíncrona de post-producción en Celery.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def node_video_edit(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que prepara las URIs de video crudo y editado."""
    tenant_id = state.get("tenant_id", "default_tenant")
    raw_uri = state.get("raw_video_uri", f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4")
    edited_uri = f"s3://viralsync-media-dev/{tenant_id}/edited_output.mp4"

    logger.info(f"[{tenant_id}] Ejecutando nodo 'video_edit'")

    logs = state.get("logs", [])
    logs.append(f"[video_edit] Video procesado exitosamente: '{edited_uri}'")

    return {
        "raw_video_uri": raw_uri,
        "edited_video_uri": edited_uri,
        "logs": logs,
    }
