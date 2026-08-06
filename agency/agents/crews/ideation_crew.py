"""
agents/crews/ideation_crew.py

CrewAI Crew para la generación de ideas de contenido basadas en los 4 cuadrantes
de competencia (AGENTS.md sección 7.7) y evaluación previa 5/50 y RUM.
"""

import os
import json
from typing import Any
from crewai import Agent, Task, Crew, Process, LLM
from agents.mcp_servers.searxng_mcp_server import searxng_search_sanitized


class DummyIdeationCrew:
    """Crew con fallback estructurado para dev/local sin API keys externas."""

    def __init__(self, tenant_id: str, niche: str, market_map: dict):
        self.tenant_id = tenant_id
        self.niche = niche
        self.market_map = market_map

    def kickoff(self) -> list[dict[str, Any]]:
        # Intentar ejecutar búsqueda vía SearXNG para incorporar contexto real
        search_query = f"tendencias reels viral {self.niche}"
        search_results = searxng_search_sanitized(search_query)

        return [
            {
                "texto": f"3 Errores fatales en {self.niche} que te están costando clientes y dinero",
                "gancho": f"Si trabajas en {self.niche}, deja de hacer esto inmediatamente...",
                "entendible_nino_5_anos": True,
                "interesa_50_de_100": True,
                "universalidad": 0.85,
                "intensidad": 0.90,
                "claridad": 0.95,
                "shareability": 0.80,
                "distribucion": 0.85,
                "alineacion": 0.90,
                "search_context": search_results[:2],
            },
            {
                "texto": f"El método poco conocido para lograr resultados en {self.niche} en menos de 30 días",
                "gancho": f"El 90% de las personas en {self.niche} ignoran esta estrategia clave...",
                "entendible_nino_5_anos": True,
                "interesa_50_de_100": True,
                "universalidad": 0.80,
                "intensidad": 0.85,
                "claridad": 0.90,
                "shareability": 0.75,
                "distribucion": 0.80,
                "alineacion": 0.85,
                "search_context": search_results[:2],
            },
        ]


def build_ideation_crew(tenant_id: str, niche: str, market_map: dict):
    # Retorna el ejecutor de ideación
    return DummyIdeationCrew(tenant_id=tenant_id, niche=niche, market_map=market_map)
