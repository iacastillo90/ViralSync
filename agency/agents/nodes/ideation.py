"""
ideation.py

Nodo de Ideación de LangGraph.
Ejecuta la crew de ideación de 4 cuadrantes y evalúa los candidatos RUM.
"""

import logging
from typing import Dict, Any
from agents.crews.ideation_crew import run_ideation_crew

logger = logging.getLogger(__name__)


def node_ideation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera ideas de contenido viral para el tenant."""
    tenant_id = state.get("tenant_id", "default_tenant")
    niche = state.get("niche", "Negocios B2B y SaaS")
    market_map = state.get("market_map", {})

    logger.info(f"[{tenant_id}] Ejecutando nodo 'ideation' para nicho '{niche}'")

    ideas = run_ideation_crew(niche=niche, market_map=market_map)
    selected_idea = ideas[0] if ideas else {}

    logs = state.get("logs", [])
    logs.append(f"[ideation] Generadas {len(ideas)} ideas RUM para tenant '{tenant_id}'")

    return {
        "ideas": ideas,
        "selected_idea": selected_idea,
        "logs": logs,
    }
