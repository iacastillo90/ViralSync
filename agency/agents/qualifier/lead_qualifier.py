"""
agents/qualifier/lead_qualifier.py

Agente calificador ligero (AGENTS.md 7.9, paso 3-4):
  "un agente calificador ligero (no un Crew completo — este debe responder
   en segundos, no minutos)"

Deliberadamente NO usa CrewAI ni pasa por el LLM gateway para el caso
común: es un match de keyword contra campañas activas cacheadas en Redis.
Solo si hace falta desambiguar (p. ej. la keyword aparece dentro de una
frase más larga y no está claro si es intencional) se hace UNA llamada
rápida al motor-agencia vía LiteLLM — nunca al fallback pagado para esto.

Su único trabajo es filtrar ruido y preparar contexto de atribución; nunca
cierra la venta ni continúa la conversación (esa frontera es deliberada,
igual que el checkpoint humano de publicación).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.cache import get_active_campaign_keywords  # {tenant_id: {keyword: video_id}}, cacheado en Redis


@dataclass
class QualifiedMatch:
    keyword: str
    video_id: str
    tenant_id: str


def qualify_lead(texto: str, entry: dict) -> QualifiedMatch | None:
    """
    Matching case-insensitive, por palabra completa (evita falsos positivos
    tipo "consultado" matcheando "consulta"). Devuelve None si no hay
    coincidencia con ninguna campaña activa — eso es ruido, se descarta
    sin persistir nada.
    """
    texto_normalizado = texto.strip().lower()

    for tenant_id, keyword_map in get_active_campaign_keywords().items():
        for keyword, video_id in keyword_map.items():
            pattern = rf"\b{re.escape(keyword.lower())}\b"
            if re.search(pattern, texto_normalizado):
                return QualifiedMatch(keyword=keyword, video_id=video_id, tenant_id=tenant_id)

    return None
