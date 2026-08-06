"""
human_approval.py

Nodos de Aprobación Humana de LangGraph (Checkpoints Manuales).
Pausan la ejecución del grafo hasta recibir el input del usuario en el dashboard.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def node_human_approval_idea(state: Dict[str, Any]) -> Dict[str, Any]:
    """Checkpoint para la aprobación de la idea candidata RUM."""
    tenant_id = state.get("tenant_id", "default_tenant")
    idea_approved = state.get("idea_approved", False)
    
    logs = state.get("logs", [])
    if idea_approved:
        logs.append(f"[human_approval_idea] Idea aprobada por el usuario para tenant '{tenant_id}'")
    else:
        logs.append(f"[human_approval_idea] Esperando aprobación humana de idea para tenant '{tenant_id}'")

    return {"logs": logs}


def node_human_approval_publish(state: Dict[str, Any]) -> Dict[str, Any]:
    """Checkpoint para la aprobación de publicación del video editado."""
    tenant_id = state.get("tenant_id", "default_tenant")
    publish_approved = state.get("publish_approved", False)

    logs = state.get("logs", [])
    if publish_approved:
        logs.append(f"[human_approval_publish] Publicación aprobada por el usuario para tenant '{tenant_id}'")
    else:
        logs.append(f"[human_approval_publish] Esperando aprobación humana de publicación para tenant '{tenant_id}'")

    return {"logs": logs}
