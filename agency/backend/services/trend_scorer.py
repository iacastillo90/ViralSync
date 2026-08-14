"""
trend_scorer.py

Motor Híbrido de Scoring de Tendencias para Guiones ViralSync.

Genera un indicador de impacto viral (0-100) por guion combinando:
  1. Análisis LLM (Gemini vía el router LiteLLM) — tendencias del nicho + estructura narrativa.
  2. Reglas heurísticas determinísticas  — presencia de palabras clave de tendencia, CTA fuerte,
     urgencia, duraciones de bloque óptimas, pregunta retórica en el gancho.

Contrato de salida: dict con claves `score` (int 0-100) y `rationale` (str ≤300 chars).

Arquitectura preparada para plug-in de modelo ML cuando el tenant acumule ≥30 registros
de métricas 72h en la tabla `video_metrics`. En ese momento, `trend_scorer.ml_refine()`
ajusta el score con el peso aprendido (feature: gancho_type, cta_tipo, niche).
"""

import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  Palabras clave de tendencia viral (año en curso) — Reglas
# ─────────────────────────────────────────────────────────────
_TREND_KEYWORDS = [
    "secreto", "nadie te dice", "antes y después", "error", "trampa",
    "gratis", "rápido", "fácil", "cómo", "revelación", "descubierto",
    "cambió mi vida", "lo que no sabías", "haz esto", "stop", "para",
    "debes saber", "viral", "tendencia", "2025", "2026", "ia", "ai",
    "chatgpt", "automatiza", "sin esfuerzo", "en minutos",
]

_CTA_POWER_PHRASES = [
    "comenta", "escríbeme", "manda", "sigue", "comparte", "guarda",
    "activa", "haz clic", "entra", "link en bio", "deja tu", "di",
    "responde", "cuéntame",
]

_RHETORICAL_MARKERS = ["?", "¿", "adivina", "sabías que", "qué pasaría si"]

# Pesos de cada categoría en la puntuación final de reglas (suma 60)
_W_KEYWORDS = 20   # keywords de tendencia en el gancho
_W_CTA      = 20   # CTA de alto impacto
_W_RHETORIC = 10   # pregunta retórica en el gancho
_W_STRUCT   = 10   # estructura de bloques no vacíos


def _score_by_rules(script: Dict[str, Any]) -> int:
    """Puntuación heurística pura (0-60) — sin llamada LLM."""
    gancho    = (script.get("gancho_0_5s") or "").lower()
    contexto  = (script.get("contexto_5_30s") or "").lower()
    moraleja  = (script.get("moraleja_30_50s") or "").lower()
    cta       = (script.get("cta_50_60s") or "").lower()
    full_text = f"{gancho} {contexto} {moraleja} {cta}"

    # 1. Keywords de tendencia (presencia mínima en el gancho)
    kw_hits = sum(1 for kw in _TREND_KEYWORDS if kw in gancho)
    kw_score = min(_W_KEYWORDS, int(kw_hits / max(len(_TREND_KEYWORDS), 1) * _W_KEYWORDS * 6))

    # 2. CTA de alto impacto
    cta_hits = sum(1 for phrase in _CTA_POWER_PHRASES if phrase in cta or phrase in full_text)
    cta_score = min(_W_CTA, int(cta_hits / max(len(_CTA_POWER_PHRASES), 1) * _W_CTA * 8))

    # 3. Pregunta retórica en el gancho
    rhetoric_score = _W_RHETORIC if any(m in gancho for m in _RHETORICAL_MARKERS) else 0

    # 4. Estructura completa (todos los bloques no vacíos)
    blocks_filled = all([gancho, contexto, moraleja, cta])
    struct_score = _W_STRUCT if blocks_filled else 0

    total = kw_score + cta_score + rhetoric_score + struct_score
    logger.debug(
        f"[trend_scorer:rules] kw={kw_score} cta={cta_score} "
        f"rhetoric={rhetoric_score} struct={struct_score} → total={total}"
    )
    return min(60, total)


async def _score_by_llm(
    script: Dict[str, Any],
    niche: str,
) -> Dict[str, Any]:
    """
    Puntúa el guion con Gemini (router LLM compartido) analizando tendencias del nicho.
    Retorna dict con claves `llm_score` (int 0-40) y `rationale` (str ≤300 chars).
    En caso de error del LLM, retorna score=20 con rationale de fallback.
    """
    try:
        import agents.llm as llm_router

        gancho    = script.get("gancho_0_5s", "")[:200]
        contexto  = script.get("contexto_5_30s", "")[:300]
        moraleja  = script.get("moraleja_30_50s", "")[:300]
        cta       = script.get("cta_50_60s", "")[:200]

        system_prompt = (
            "Eres un analista experto en viralidad de contenido corto (Reels/TikTok). "
            "Tu tarea es evaluar un guion estructurado en 4 bloques y devolver ÚNICAMENTE "
            "un JSON con dos claves: \"llm_score\" (int 0-40) y \"rationale\" (str ≤250 chars). "
            "Evalúa: (1) alineación con tendencias actuales del nicho, (2) potencia del gancho "
            "en los primeros 5s para retener al espectador, (3) claridad de la propuesta de valor, "
            "(4) efectividad del CTA para conversión. "
            "Responde ÚNICAMENTE con el JSON, sin texto adicional."
        )

        user_prompt = (
            f"Nicho: {niche}\n\n"
            f"Gancho (0-5s): {gancho}\n"
            f"Contexto (5-30s): {contexto}\n"
            f"Moraleja (30-50s): {moraleja}\n"
            f"CTA (50-60s): {cta}\n\n"
            "Evalúa este guion y devuelve el JSON:"
        )

        content = (
            await llm_router.acomplete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=256,
            )
        ).strip()

        # Aislar el JSON de la respuesta
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            llm_score  = max(0, min(40, int(parsed.get("llm_score", 20))))
            rationale  = str(parsed.get("rationale", ""))[:300]
            return {"llm_score": llm_score, "rationale": rationale}

    except Exception as exc:
        logger.warning(f"[trend_scorer:llm] Error al puntuar con LLM: {exc}")

    # Fallback seguro
    return {
        "llm_score": 20,
        "rationale": "Score calculado por motor de reglas (LLM no disponible).",
    }


async def score_script(
    script: Dict[str, Any],
    niche: str = "Marketing y Negocios",
) -> Dict[str, Any]:
    """
    Punto de entrada principal del scorer híbrido.

    Combina:
     - Hasta 60 puntos de reglas heurísticas determinísticas.
     - Hasta 40 puntos del análisis LLM de tendencias.

    :param script: Dict con los 4 bloques del guion (gancho_0_5s, contexto_5_30s,
                   moraleja_30_50s, cta_50_60s).
    :param niche:  Nicho del cliente para contextualizar el análisis LLM.
    :return: {'score': int 0-100, 'rationale': str}
    """
    rule_score = _score_by_rules(script)
    llm_result = await _score_by_llm(script, niche)

    total_score = rule_score + llm_result["llm_score"]
    total_score = max(0, min(100, total_score))

    logger.info(
        f"[trend_scorer] Reglas={rule_score}/60 | LLM={llm_result['llm_score']}/40 | "
        f"Total={total_score}/100 | Nicho='{niche}'"
    )

    return {
        "score": total_score,
        "rationale": llm_result["rationale"],
    }
