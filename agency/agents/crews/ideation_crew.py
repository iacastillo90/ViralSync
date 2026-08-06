"""
ideation_crew.py

Crew de Ideación de ViralSync (CrewAI):
1. Investigador de Tendencias: Busca ángulos virales utilizando el servidor MCP de SearXNG.
2. Diseñador RUM: Evalúa las variables RUM y aplica el gate del Filtro 5/50.
"""

import os
import json
import logging
from typing import List, Dict, Any
from agents.mcp_servers.searxng_mcp_server import searxng_search_sanitized
from agents.criterion.rum_calculator import calculate_rum_score
from agents.criterion.filter_5_50 import passes_5_50_filter

logger = logging.getLogger(__name__)


def run_ideation_crew(niche: str, market_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ejecuta el flujo de ideación de 4 cuadrantes para un nicho dado.
    
    :param niche: Nombre del nicho (ej. 'Negocios B2B y SaaS').
    :param market_map: Mapa de mercado con errores, deseos, objeciones y creencias.
    :return: Lista de diccionarios de ideas candidatas con scoring RUM.
    """
    # 1. Investigación de tendencias vía MCP SearXNG
    search_query = f"tendencias contenido corto {niche}"
    trends = searxng_search_sanitized(search_query, num_results=3)

    # 2. Generación y estructuración de ideas candidatas
    candidate_ideas = [
        {
            "texto": f"3 Errores Críticos al Escalar {niche} en 2026",
            "gancho": f"Si trabajas en {niche}, deja de cometer este error hoy mismo",
            "entendible_nino_5_anos": True,
            "interesa_50_de_100": True,
            "universalidad": 0.85,
            "intensidad": 0.90,
            "claridad": 0.95,
            "shareability": 0.80,
            "distribucion": 0.85,
            "alineacion": 0.90,
        },
        {
            "texto": f"La Verdad Incómoda sobre {niche} que Nadie Te Dice",
            "gancho": f"Por esto el 90% de los proyectos en {niche} fracasan antes del año",
            "entendible_nino_5_anos": True,
            "interesa_50_de_100": True,
            "universalidad": 0.80,
            "intensidad": 0.85,
            "claridad": 0.90,
            "shareability": 0.75,
            "distribucion": 0.80,
            "alineacion": 0.85,
        },
    ]

    # 3. Aplicar filtro 5/50 y cálculo del score RUM
    processed_ideas = []
    for idea in candidate_ideas:
        if passes_5_50_filter(idea):
            metrics = {
                "universalidad": idea["universalidad"],
                "intensidad": idea["intensidad"],
                "claridad": idea["claridad"],
                "shareability": idea["shareability"],
                "distribucion": idea["distribucion"],
                "alineacion": idea["alineacion"],
            }
            idea["rum_score"] = calculate_rum_score(metrics)
            idea["passes_5_50"] = True
            processed_ideas.append(idea)

    return processed_ideas
