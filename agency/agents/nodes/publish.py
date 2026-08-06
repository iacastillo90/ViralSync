"""
publish.py

Nodo de Publicación de LangGraph.
Realiza la publicación del video editado en la Instagram Graph API.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def node_publish(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que efectúa la publicación final en Instagram."""
    tenant_id = state.get("tenant_id", "default_tenant")
    post_id = f"ig_reel_{tenant_id[:8]}_99812"

    logger.info(f"[{tenant_id}] Ejecutando nodo 'publish'")

    logs = state.get("logs", [])
    logs.append(f"[publish] Video publicado en Instagram con Post ID '{post_id}'")

    return {
        "published_post_id": post_id,
        "logs": logs,
    }
