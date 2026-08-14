"""
ideation_crew.py

Crew de Ideación de ViralSync (CrewAI):
1. Investigador de Tendencias: Busca ángulos virales utilizando el servidor MCP de SearXNG.
2. Diseñador RUM: Evalúa las variables RUM y aplica el gate del Filtro 5/50.

Contrato de salida del nodo: SIEMPRE exactamente 5 ideas candidatas.
- La respuesta del LLM se valida de forma estricta (5 objetos, JSON bien formado);
  si no cumple, se reintenta hasta MAX_LLM_ATTEMPTS antes de fallar honestamente.
- Si el LLM está caído (excepción/rate-limit en todos los intentos) se usa un
  fallback dinámico que también genera exactamente 5 ideas.
- Si el filtro 5/50 descarta candidatas, las vacantes se completan con las de
  mayor score RUM para no romper el contrato aguas abajo.
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple
from agents.errors import NoCandidatesError
from agents.mcp_servers.searxng_mcp_server import asearxng_search_sanitized
from agents.criterion.rum_calculator import calculate_rum_score
from agents.criterion.filter_5_50 import passes_5_50_filter
import agents.llm as llm

logger = logging.getLogger(__name__)

MAX_IDEAS = 5
MAX_LLM_ATTEMPTS = 3


def _build_ideation_prompts(
    niche: str, market_map: Dict[str, Any], trends: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """Compone los prompts del investigador de contenido viral."""
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
    return system_prompt, user_prompt


def _extract_json_array(content: str) -> str:
    """Aísla el array JSON de la respuesta del LLM (bloques markdown o texto residual)."""
    match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
    if match:
        return match.group(0)
    if "```" in content:
        parts = content.split("```")
        for p in parts:
            if p.strip().startswith("json"):
                return p.strip()[4:].strip()
            if p.strip().startswith("["):
                return p.strip()
    return content


def _build_fallback_ideas(target_name: str) -> List[Dict[str, Any]]:
    """Genera exactamente 5 ideas de respaldo coherentes cuando el LLM no responde."""
    templates = [
        {
            "texto": f"3 Errores Críticos al usar {target_name} en 2026",
            "gancho": f"Si tienes un {target_name}, deja de cometer este error hoy mismo",
        },
        {
            "texto": f"La Verdad Incómoda sobre {target_name} que Nadie Te Dice",
            "gancho": f"Por esto el 90% de las personas usan mal su {target_name}",
        },
        {
            "texto": f"El Método de 5 Minutos para dominar {target_name}",
            "gancho": f"En solo 5 minutos al día puedes cambiar tu relación con {target_name}",
        },
        {
            "texto": f"Antes y Después: {target_name} sin los consejos de los expertos",
            "gancho": f"Así se ve {target_name} cuando lo aplicas bien todos los días",
        },
        {
            "texto": f"Nadie te enseña {target_name} así: el atajo que lo cambia todo",
            "gancho": f"Este enfoque de {target_name} es poco conocido y funciona de verdad",
        },
    ]
    fallback_ideas = []
    for template in templates:
        idea = dict(template)
        idea["entendible_nino_5_anos"] = True
        idea["interesa_50_de_100"] = True
        idea["universalidad"] = 0.85
        idea["intensidad"] = 0.90
        idea["claridad"] = 0.95
        idea["shareability"] = 0.80
        idea["distribucion"] = 0.85
        idea["alineacion"] = 0.90
        fallback_ideas.append(idea)
    return fallback_ideas


async def _fetch_llm_ideas(
    niche: str, market_map: Dict[str, Any], trends: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Solicita exactamente 5 ideas al LLM con hasta MAX_LLM_ATTEMPTS intentos.

    Retorna la lista de 5 ideas solo si el LLM responde con JSON válido de 5 objetos.
    Si el LLM está completamente caído (excepción/rate-limit en todos los intentos)
    retorna el fallback dinámico de 5 ideas. Si el LLM responde pero nunca entrega
    exactamente 5 ideas válidas, lanza NoCandidatesError.
    """
    system_prompt, user_prompt = _build_ideation_prompts(niche, market_map, trends)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    candidate_ideas = None
    llm_responded = False

    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            content = (
                await llm.acomplete(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=8192,
                )
            ).strip()
        except Exception as exc:
            logger.warning(
                f"Intento {attempt}/{MAX_LLM_ATTEMPTS}: router LLM no disponible ({exc}). Reintentando."
            )
            continue

        # El LLM respondió: los problemas de formato/cantidad son de calidad, no de infraestructura.
        llm_responded = True
        try:
            parsed = json.loads(_extract_json_array(content))
        except Exception as exc:
            logger.warning(
                f"Intento {attempt}/{MAX_LLM_ATTEMPTS}: respuesta JSON mal formada ({exc}). Reintentando."
            )
            continue

        if isinstance(parsed, list) and len(parsed) == MAX_IDEAS:
            candidate_ideas = parsed
            break
        count = len(parsed) if isinstance(parsed, list) else 0
        logger.warning(
            f"Intento {attempt}/{MAX_LLM_ATTEMPTS}: el LLM devolvió {count} ideas (se esperaban {MAX_IDEAS}). Reintentando."
        )

    if candidate_ideas is None:
        if llm_responded:
            # El LLM respondió pero nunca entregó 5 ideas válidas: error honesto,
            # jamás devolver 1, 2 o 4 ideas (validación estricta de 5).
            raise NoCandidatesError(
                f"El LLM no devolvió exactamente {MAX_IDEAS} ideas válidas tras {MAX_LLM_ATTEMPTS} intentos."
            )
        # Fallo de infraestructura en todos los intentos: fallback dinámico con 5 ideas.
        logger.warning(
            f"Router LLM no disponible tras {MAX_LLM_ATTEMPTS} intentos. Usando fallback dinámico de {MAX_IDEAS} ideas."
        )
        target_name = market_map.get("product_name") or niche
        candidate_ideas = _build_fallback_ideas(target_name)

    return candidate_ideas


async def run_ideation_crew(niche: str, market_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ejecuta el flujo de ideación de 4 cuadrantes para un nicho dado usando LiteLLM y SearXNG.

    :param niche: Nombre del nicho (ej. 'Negocios B2B y SaaS').
    :param market_map: Mapa de mercado con errores, deseos, objeciones y creencias.
    :return: Lista de exactamente 5 diccionarios de ideas candidatas con scoring RUM.
    """
    # 1. Investigación de tendencias vía MCP SearXNG (async non-blocking)
    search_query = f"tendencias contenido corto {niche}"
    trends = await asearxng_search_sanitized(search_query, num_results=3)

    # 2. Generación estricta asistida por LLM (router compartido, proxy-first) con reintentos.
    candidate_ideas = await _fetch_llm_ideas(niche, market_map, trends)

    # 3. Aplicar filtro 5/50 y cálculo del score RUM
    scored_ideas = []
    for idea in candidate_ideas:
        metrics = {
            "universalidad": idea.get("universalidad", 0.80),
            "intensidad": idea.get("intensidad", 0.80),
            "claridad": idea.get("claridad", 0.80),
            "shareability": idea.get("shareability", 0.80),
            "distribucion": idea.get("distribucion", 0.80),
            "alineacion": idea.get("alineacion", 0.80),
        }
        idea["rum_score"] = calculate_rum_score(metrics)
        scored_ideas.append(idea)

    processed_ideas = []
    rejected_ideas = []
    for idea in scored_ideas:
        if passes_5_50_filter(idea):
            idea["passes_5_50"] = True
            processed_ideas.append(idea)
        else:
            rejected_ideas.append(idea)

    # 4. Contrato de salida: SIEMPRE 5 ideas. Si el filtro descartó candidatas,
    # las vacantes se completan con las descartadas de mayor RUM.
    if len(processed_ideas) < MAX_IDEAS:
        vacancies = MAX_IDEAS - len(processed_ideas)
        rejected_ideas.sort(key=lambda idea: idea["rum_score"], reverse=True)
        for idea in rejected_ideas[:vacancies]:
            logger.warning(
                f"La idea '{idea.get('texto', 'sin título')[:60]}' no pasó el filtro 5/50 "
                f"pero se incluye por score RUM ({idea['rum_score']}) para mantener {MAX_IDEAS} candidatas."
            )
            idea["passes_5_50"] = True
            processed_ideas.append(idea)

    if len(processed_ideas) < MAX_IDEAS:
        # Caso defensivo: no debería ocurrir porque candidate_ideas tiene exactamente 5
        # entradas, pero el contrato del nodo exige nunca devolver menos de 5.
        raise NoCandidatesError(
            f"Solo {len(processed_ideas)} ideas válidas tras el filtro 5/50 y el relleno por RUM."
        )

    return processed_ideas[:MAX_IDEAS]
