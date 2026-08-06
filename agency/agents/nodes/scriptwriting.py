"""
scriptwriting.py

Nodo de Guionismo de LangGraph.
Ejecuta la crew de guionismo de 4 bloques a partir de la idea aprobada.
"""

import logging
from typing import Dict, Any
from agents.crews.scriptwriting_crew import run_scriptwriting_crew

logger = logging.getLogger(__name__)


def node_scriptwriting(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera el guion en 4 bloques."""
    tenant_id = state.get("tenant_id", "default_tenant")
    selected_idea = state.get("selected_idea", {})
    niche_ppp = state.get("niche_ppp", "")

    logger.info(f"[{tenant_id}] Ejecutando nodo 'scriptwriting'")

    script = run_scriptwriting_crew(idea=selected_idea, niche_ppp=niche_ppp)

    logs = state.get("logs", [])
    logs.append(f"[scriptwriting] Guion de 4 bloques generado con palabra clave '{script.get('keyword')}'")

    return {
        "script": script,
        "logs": logs,
    }
