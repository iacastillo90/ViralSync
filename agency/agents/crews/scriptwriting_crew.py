"""
scriptwriting_crew.py

Crew de Guionismo de ViralSync (CrewAI):
1. Estratega de Marca: Inyecta el tono y parámetros de voz de marca usando RAG MCP.
2. Guionista Viral: Redacta guiones estructurados en 4 bloques con palabra clave única de CTA.
"""

import json
import logging
from typing import Dict, Any
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge
from agents.criterion.ppp_validator import validate_ppp_structure
import agents.llm as llm

logger = logging.getLogger(__name__)


async def run_scriptwriting_crew(
    idea: Dict[str, Any], niche_ppp: str = ""
) -> Dict[str, Any]:
    """
    Genera un guion viral en 4 bloques a partir de una idea aprobada RUM usando LiteLLM y RAG context.
    
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

    script = {}

    # 3. Generación asistida por LLM (router compartido, proxy-first)
    try:
        system_prompt = (
            "Eres un Guionista Viral de elite para Instagram Reels y TikTok. "
            "Redacta un guion hiper-efectivo estructurado en exactamente 4 bloques cronológicos y una palabra clave de CTA. "
            "Responde ÚNICAMENTE con un objeto JSON sin formato markdown."
        )

        user_prompt = (
            f"Título de la idea: {idea_title}\n"
            f"Gancho inicial sugerido: {gancho_base}\n"
            f"Promesa Principal de Producto (PPP): {niche_ppp}\n"
            f"Contexto de Marca (RAG): {json.dumps(brand_context, ensure_ascii=False)}\n\n"
            "Devuelve un objeto JSON con la siguiente estructura exacta:\n"
            "{\n"
            '  "gancho_0_5s": "Frase de gancho inicial (0-5s)",\n'
            '  "contexto_5_30s": "Desarrollo del problema y contexto (5-30s)",\n'
            '  "moraleja_30_50s": "Moraleja o solución clave (30-50s)",\n'
            '  "cta_50_60s": "Llamada a la acción clara instando a comentar una palabra clave (50-60s)",\n'
            '  "keyword": "PALABRA_CLAVE"\n'
            "}"
        )

        content = (
            await llm.acomplete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
        ).strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "gancho_0_5s" in parsed:
            script = parsed
    except Exception as exc:
        logger.warning(f"Router LLM no disponible para guionismo ({exc}). Usando fallback dinámico.")

    # Fallback dinámico si el LLM no está disponible
    if not script:
        script = {
            "gancho_0_5s": gancho_base,
            "contexto_5_30s": (
                f"En {idea_title}, el problema principal no es la falta de herramientas, sino intentar abarcar todo sin foco. "
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

