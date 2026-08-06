"""
agents/crews/scriptwriting_crew.py

CrewAI Crew para la generación del guion estructurado en 4 bloques.
(AGENTS.md secciones 7.3, 7.4 y 7.5)
"""

import os
import json
from typing import Any
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge


class DummyScriptwritingCrew:
    """Crew con fallback estructurado para dev/local sin API keys externas."""

    def __init__(self, tenant_id: str, idea: dict):
        self.tenant_id = tenant_id
        self.idea = idea

    def kickoff(self) -> dict[str, Any]:
        # Consultar personaje de marca vía RAG MCP
        rag_context = query_rag_knowledge(f"personaje de marca tenant {self.tenant_id}")

        niche_topic = self.idea.get("texto", "Estrategia clave")
        keyword = f"CONSULTA_{self.tenant_id[:4].upper()}"

        return {
            "gancho_0_5s": f"¡Detente! Si quieres dominar {niche_topic}, necesitas ver esto antes de continuar.",
            "contexto_5_30s": "La mayoría comete el error de enfocarse en el método tradicional sin entender cómo funciona la retención del algoritmo moderno...",
            "moraleja_30_50s": "El secreto está en simplificar tu oferta en una Promesa Principal concreta: resultados medibles en 30 días sin complicaciones.",
            "cta_50_60s": f"Comenta la palabra clave '{keyword}' abajo y te enviaré la guía completa por mensaje directo.",
            "keyword": keyword,
            "brand_context": rag_context,
        }


def build_scriptwriting_crew(tenant_id: str, idea: dict):
    return DummyScriptwritingCrew(tenant_id=tenant_id, idea=idea)
