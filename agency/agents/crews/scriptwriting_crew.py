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
from agents.crews.prompt_context import build_trend_section, resolve_rum_threshold
import agents.llm as llm

logger = logging.getLogger(__name__)


async def run_scriptwriting_crew(
    idea: Dict[str, Any], 
    niche_ppp: str = "",
    product_name: str = None,
    product_description: str = None,
    target_duration: int = 30,
) -> Dict[str, Any]:
    """
    Genera un guion viral en 4 bloques a partir de una idea aprobada RUM usando LiteLLM y RAG context.
    
    :param idea: Diccionario de la idea aprobada (texto, gancho, rum_score).
    :param niche_ppp: Promesa Principal de Producto del nicho.
    :param product_name: Nombre específico del producto o servicio.
    :param product_description: Descripción detallada del producto o servicio.
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
    niche = product_name or idea.get("niche", "Producto / Servicio General")

    script = {}

    # 3. Generación asistida por LLM (router compartido, proxy-first)
    try:
        rum_threshold = resolve_rum_threshold(niche)
        trend_section = build_trend_section(niche)
        trend_line = (
            f"Trending topics ({niche}):\n{trend_section}\n"
            if trend_section
            else ""
        )

        system_prompt = (
            "Eres un Guionista Viral de elite para Instagram Reels y TikTok. "
            "Redacta un guion hiper-efectivo estructurado en exactamente 4 bloques cronológicos y una palabra clave de CTA. "
            "IMPORTANTE: El guion DEBE enfocarse EXCLUSIVAMENTE en el producto o servicio especificado. "
            "NO menciones conceptos ajenos como 'SaaS', 'conversión de leads en software' o 'consultoría B2B' a menos que el producto lo requiera explícitamente. "
            "Responde ÚNICAMENTE con un objeto JSON sin formato markdown."
        )

        prod_ctx = f"Producto: {product_name}\nDescripción del Producto: {product_description}\n" if product_name else ""
        word_guide = {
            15: "EXACTAMENTE 31 palabras en total (ritmo ultra-rápido 15 segundos)",
            30: "EXACTAMENTE 70 palabras en total (ritmo dinámico 30 segundos - Recomendado)",
            45: "EXACTAMENTE 105 palabras en total (ritmo explicado 45 segundos)",
            60: "EXACTAMENTE 140 palabras en total (ritmo completo y detallado 60 segundos)",
        }.get(target_duration, "EXACTAMENTE 70 palabras en total (30 segundos)")

        # Contexto RAG de patrones virales aprendidos en Qdrant
        rag_pattern_lines = ""
        try:
            from backend.services.rag_context import get_winning_patterns
            winning_patterns = get_winning_patterns(niche=niche, query=idea_title, limit=3)
            if winning_patterns:
                p_text = "\n".join([f"- Patrón (Score {p.get('viral_score', 0.8):.2f}): \"{p.get('pattern_text', '')}\"" for p in winning_patterns if p.get('pattern_text')])
                if p_text:
                    rag_pattern_lines = f"Patrones Virales Ganadores del Nicho (Qdrant RAG Memory):\n{p_text}\nUtiliza estos patrones como referencia para elevar la viralidad del gancho.\n"
        except Exception as rag_err:
            logger.warning(f"No se pudo obtener contexto RAG de Qdrant: {rag_err}")

        user_prompt = (
            f"Título de la idea: {idea_title}\n"
            f"Gancho inicial sugerido: {gancho_base}\n"
            f"{prod_ctx}"
            f"Duración objetivo del Reel: {target_duration} segundos ({word_guide}).\n"
            f"Promesa Principal de Producto (PPP): {niche_ppp}\n"
            f"Target RUM threshold ({niche}): {rum_threshold:.2f}\n"
            f"{trend_line}"
            f"{rag_pattern_lines}"
            "Devuelve un objeto JSON con la siguiente estructura exacta:\n"
            "{\n"
            '  "gancho_0_5s": "Frase de gancho inicial (0-5s)",\n'
            '  "contexto_5_30s": "Desarrollo del problema y contexto alineado al producto (5-30s)",\n'
            '  "moraleja_30_50s": "Moraleja o solución clave enfocada en el valor del producto (30-50s)",\n'
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

        import re
        match = re.search(r'\{\s*".*\}\s*', content, re.DOTALL)
        if match:
            content = match.group(0)
        else:
            if "```" in content:
                parts = content.split("```")
                for p in parts:
                    if p.strip().startswith("json"):
                        content = p.strip()[4:].strip()
                        break
                    elif p.strip().startswith("{"):
                        content = p.strip()
                        break
                        
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "gancho_0_5s" in parsed:
            script = parsed
    except Exception as exc:
        logger.warning(f"Router LLM no disponible para guionismo ({exc}). Usando fallback dinámico.")

    # Fallback dinámico si el LLM no está disponible (adaptado a target_duration)
    if not script:
        keyword = "CONFIGURACIÓN" if ("K688" in (product_name or idea_title) or "Micrófono" in (product_name or idea_title)) else "CONSULTA"
        p_name = product_name or idea_title

        if target_duration <= 15:
            script = {
                "gancho_0_5s": gancho_base,
                "contexto_5_30s": f"Con {p_name}, optimizas tu resultado al instante sin complicaciones.",
                "moraleja_30_50s": "Ajusta la configuración adecuada y ahorra tiempo.",
                "cta_50_60s": f"Comenta '{keyword}' para la guía rápida.",
                "keyword": keyword,
            }
        elif target_duration <= 30:
            script = {
                "gancho_0_5s": gancho_base,
                "contexto_5_30s": f"Al usar {p_name}, es común cometer errores de ajuste y posición que afectan la calidad final de tu contenido.",
                "moraleja_30_50s": "Con la configuración correcta de niveles y monitoreo en tiempo real, obtienes un resultado profesional al instante.",
                "cta_50_60s": f"Comenta '{keyword}' si deseas la guía paso a paso.",
                "keyword": keyword,
            }
        elif target_duration <= 45:
            script = {
                "gancho_0_5s": gancho_base,
                "contexto_5_30s": f"Al utilizar {p_name}, el problema principal no es el equipo sino intentar abarcar todo sin una configuración adecuada. Ajustar niveles y supresión de ruido transforma tus resultados.",
                "moraleja_30_50s": "No necesitas invertir fortunas en herramientas complejas antes de dominar lo que ya tienes. Conocer las funciones clave de tu equipo garantiza tracción orgánica sin fricción.",
                "cta_50_60s": f"Comenta la palabra '{keyword}' abajo y te enviamos el desglose estratégico por DM.",
                "keyword": keyword,
            }
        else: # 60s - Calibrado a 140 palabras exactas para durar 60s
            script = {
                "gancho_0_5s": f"Si utilizas {p_name}, detén las grabaciones ruidosas hoy mismo y optimiza tu audio.",
                "contexto_5_30s": f"Al producir contenido con {p_name}, muchos usuarios cometen errores críticos que reducen el rendimiento de su producción. La ganancia desajustada, la posición incorrecta y la falta de monitoreo generan interferencias que comprometen la calidad. Ya seas creador o podcaster, entender la cápsula cardioide dinámica te permite aislar tu voz y eliminar reflejos ambientales no deseados de inmediato.",
                "moraleja_30_50s": "La clave para escalar la presencia de tu marca es optimizar tus herramientas al máximo de su capacidad. Dominar la flexibilidad de la conexión USB y XLR te otorga grabaciones limpias sin gastar fortunas en estudios costosos. Entregar un audio impecable sin fricción triplica la confianza y el engagement de tu audiencia de forma sostenible.",
                "cta_50_60s": f"Comenta la palabra clave '{keyword}' abajo si deseas descargar la guía completa para configurar tu equipo profesionalmente sin errores.",
                "keyword": keyword,
            }

    # Calibración matemática exacta de palabras para Edge-TTS (~2.3 palabras por segundo + pausas)
    max_words = {15: 32, 30: 72, 45: 108, 60: 145}.get(target_duration, int(target_duration * 2.3))
    full_text = f"{script.get('gancho_0_5s', '')} {script.get('contexto_5_30s', '')} {script.get('moraleja_30_50s', '')} {script.get('cta_50_60s', '')}".strip()
    words = full_text.split()

    if len(words) > max_words:
        logger.info(f"Ajustando guion de {len(words)} palabras al límite estricto de {max_words} palabras para {target_duration}s.")
        contexto_words = script.get("contexto_5_30s", "").split()
        excess = len(words) - max_words
        target_contexto_len = max(10, len(contexto_words) - excess)
        script["contexto_5_30s"] = " ".join(contexto_words[:target_contexto_len])
        if not script["contexto_5_30s"].endswith("."):
            script["contexto_5_30s"] += "."

    return script

