"""
ideation_crew.py

Crew de Ideación de ViralSync (CrewAI):
1. Investigador de Tendencias: Busca ángulos virales utilizando el servidor MCP de SearXNG.
2. Diseñador RUM: Evalúa las variables RUM y aplica el gate del Filtro 5/50.
"""

import re
import json
import logging
from typing import List, Dict, Any
from agents.mcp_servers.searxng_mcp_server import asearxng_search_sanitized
from agents.criterion.rum_calculator import calculate_rum_score
from agents.criterion.filter_5_50 import passes_5_50_filter
import agents.llm as llm

logger = logging.getLogger(__name__)


async def run_ideation_crew(niche: str, market_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ejecuta el flujo de ideación de 4 cuadrantes para un nicho dado usando LiteLLM y SearXNG.
    
    :param niche: Nombre del nicho (ej. 'Negocios B2B y SaaS').
    :param market_map: Mapa de mercado con errores, deseos, objeciones y creencias.
    :return: Lista de diccionarios de ideas candidatas con scoring RUM.
    """
    # 1. Investigación de tendencias vía MCP SearXNG (async non-blocking)
    search_query = f"tendencias contenido corto {niche}"
    trends = await asearxng_search_sanitized(search_query, num_results=3)


    candidate_ideas = []

    # 2. Generación dinámica asistida por LLM (router compartido, proxy-first)
    try:
        system_prompt = (
            "Eres un Investigador de Contenido Viral experto en Instagram Reels y TikTok. "
            "Tu objetivo es proponer 5 ideas de alto impacto viral estructuradas en formato JSON. "
            "Responde ÚNICAMENTE con un array JSON válido sin bloques markdown ```json ... ``` ni texto adicional."
        )

        product_context = ""
        product_name = market_map.get("product_name")
        if product_name:
            product_context = f"\nProducto/Servicio principal: {product_name}\nDescripción del producto: {market_map.get('product_description', '')}\n"

        user_prompt = (
            f"Nicho: {niche}\n"
            f"{product_context}"
            f"Tendencias actuales del mercado (SearXNG):\n{json.dumps(trends, ensure_ascii=False)}\n\n"
            f"Mapa de Mercado:\n{json.dumps(market_map, ensure_ascii=False)}\n\n"
            "Genera exactamente 5 ideas en formato JSON con la siguiente estructura por objeto:\n"
            "[\n"
            "  {\n"
            '    "texto": "Título de la idea",\n'
            '    "gancho": "Frase de gancho inicial impactante (0-5s)",\n'
            '    "entendible_nino_5_anos": true,\n'
            '    "interesa_50_de_100": true,\n'
            '    "universalidad": 0.85,\n'
            '    "intensidad": 0.90,\n'
            '    "claridad": 0.95,\n'
            '    "shareability": 0.80,\n'
            '    "distribucion": 0.85,\n'
            '    "alineacion": 0.90\n'
            "  }\n"
            "]"
        )

        content = (
            await llm.acomplete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
        ).strip()

        # Limpieza robusta del JSON, ya que algunos LLM incluyen texto antes o después
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            content = match.group(0)
        else:
            # Intento secundario: limpiar bloques markdown
            if "```" in content:
                parts = content.split("```")
                for p in parts:
                    if p.strip().startswith("json"):
                        content = p.strip()[4:].strip()
                        break
                    elif p.strip().startswith("["):
                        content = p.strip()
                        break
                        
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) > 0:
            candidate_ideas = parsed
    except Exception as exc:
        logger.warning(f"Router LLM no disponible o error en respuesta ({exc}). Usando fallback dinámico.")

    # Fallback si el LLM falla por completo en devolver algo
    if not candidate_ideas:
        pass

    # 3. Aplicar filtro 5/50 y cálculo del score RUM
    processed_ideas = []
    for idea in candidate_ideas:
        if passes_5_50_filter(idea):
            metrics = {
                "universalidad": idea.get("universalidad", 0.80),
                "intensidad": idea.get("intensidad", 0.80),
                "claridad": idea.get("claridad", 0.80),
                "shareability": idea.get("shareability", 0.80),
                "distribucion": idea.get("distribucion", 0.80),
                "alineacion": idea.get("alineacion", 0.80),
            }
            idea["rum_score"] = calculate_rum_score(metrics)
            idea["passes_5_50"] = True
            processed_ideas.append(idea)

    # Si ninguna idea del LLM superó el filtro, usar el fallback dinámico
    if not processed_ideas:
        logger.warning(f"Ninguna idea superó el filtro 5/50. Usando fallback dinámico.")
        target_name = market_map.get("product_name") or niche
        fallback_ideas = [
            {
                "texto": f"3 Errores Críticos al usar {target_name} en 2026",
                "gancho": f"Si tienes un {target_name}, deja de cometer este error hoy mismo",
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
                "texto": f"La Verdad Incómoda sobre {target_name} que Nadie Te Dice",
                "gancho": f"Por esto el 90% de las personas usan mal su {target_name}",
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
        for idea in fallback_ideas:
            metrics = {
                "universalidad": idea.get("universalidad", 0.80),
                "intensidad": idea.get("intensidad", 0.80),
                "claridad": idea.get("claridad", 0.80),
                "shareability": idea.get("shareability", 0.80),
                "distribucion": idea.get("distribucion", 0.80),
                "alineacion": idea.get("alineacion", 0.80),
            }
            idea["rum_score"] = calculate_rum_score(metrics)
            idea["passes_5_50"] = True
            processed_ideas.append(idea)

    return processed_ideas

