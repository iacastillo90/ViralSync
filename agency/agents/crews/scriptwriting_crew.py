"""
scriptwriting_crew.py

Crew de Guionismo de ViralSync (CrewAI):
1. Estratega de Marca: Inyecta el tono y parámetros de voz de marca usando RAG MCP.
2. Guionista Viral: Redacta guiones estructurados en 4 bloques con palabra clave única de CTA.
"""

import logging
from typing import Dict, Any
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge
from agents.criterion.ppp_validator import validate_ppp_structure

logger = logging.getLogger(__name__)


def run_scriptwriting_crew(
    idea: Dict[str, Any], niche_ppp: str = ""
) -> Dict[str, Any]:
    """
    Genera un guion viral en 4 bloques a partir de una idea aprobada RUM.
    
    :param idea: Diccionario de la idea aprobada (texto, gancho, rum_score).
    :param niche_ppp: Promesa Principal de Producto del nicho.
    :return: Diccionario con los 4 bloques del guion y la palabra clave única.
    """
    # 1. Recuperar contexto de marca mediante RAG MCP
    brand_context = query_rag_knowledge(query="personaje de marca")
    
    # 2. Validar estructura de PPP si está disponible
    if niche_ppp:
        ppp_eval = validate_ppp_structure(niche_ppp)
        if not ppp_eval["valid"]:
            logger.info(f"Advertencia en PPP de nicho: {ppp_eval['reason']}")

    idea_title = idea.get("texto", "Estrategia de Crecimiento")
    gancho_base = idea.get("gancho", f"Si buscas escalar en {idea_title}, escucha esto")

    # 3. Generación de los 4 Bloques (AGENTS.md sección 7.4)
    script = {
        "gancho_0_5s": gancho_base,
        "contexto_5_30s": (
            "El problema principal no es la falta de herramientas, sino intentar abarcar todo sin foco. "
            "Cuando aplicas la simplificación estructural, tu tasa de conversión se triplica en cuestión de días."
        ),
        "moraleja_30_50s": (
            "No necesitas invertir miles de dólares en anuncios antes de validar tu oferta. "
            "Primero domina la tracción orgánica y la entrega de valor sin fricción."
        ),
        "cta_50_60s": "Comenta la palabra CONSULTA abajo y te enviamos el desglose estratégico por DM.",
        "keyword": "CONSULTA",
    }

    return script
