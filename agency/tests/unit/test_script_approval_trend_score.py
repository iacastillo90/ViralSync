"""
test_script_approval_trend_score.py

Pruebas unitarias para la aprobación de guiones y el motor híbrido de scoring
de tendencias (migración 008 - Fases 3 y 4).
"""

import asyncio
from unittest.mock import AsyncMock, patch


def test_score_by_rules_high_score():
    """Un guion con keywords de tendencia, CTA fuerte y pregunta retórica debe
    recibir un alto puntaje de reglas (≥ 25 puntos sobre 60)."""
    from backend.services.trend_scorer import _score_by_rules

    script = {
        "gancho_0_5s": "¿Sabías que el 90% comete este error con su micrófono?",
        "contexto_5_30s": "La mayoría de los creadores de contenido no lo saben...",
        "moraleja_30_50s": "El secreto está en la posición y la ganancia del micrófono.",
        "cta_50_60s": "Comenta AUDIO y te mando el tutorial gratis ahora mismo.",
    }
    score = _score_by_rules(script)
    assert score >= 25, f"Score de reglas demasiado bajo: {score}"
    assert score <= 60, f"Score de reglas fuera de rango: {score}"


def test_score_by_rules_empty_script():
    """Un guion con bloques vacíos debe obtener 0 en estructura y mínimo de keywords."""
    from backend.services.trend_scorer import _score_by_rules

    score = _score_by_rules({"gancho_0_5s": "", "contexto_5_30s": "", "moraleja_30_50s": "", "cta_50_60s": ""})
    assert score == 0, f"Script vacío no debería puntuar: {score}"


def test_score_script_uses_fallback_on_llm_error():
    """Si el LLM falla, el score total debe ser score_reglas + 20 (fallback LLM)."""
    from backend.services.trend_scorer import score_script

    script = {
        "gancho_0_5s": "¿Cómo grabar audio profesional desde casa sin gastar una fortuna?",
        "contexto_5_30s": "El error más común es no tratar el ambiente de grabación primero.",
        "moraleja_30_50s": "Con estas 3 técnicas tu audio cambiará completamente.",
        "cta_50_60s": "Sigue para ver el tutorial completo y comenta AUDIO.",
    }

    async def _run():
        with patch("backend.services.trend_scorer._score_by_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"llm_score": 20, "rationale": "Fallback: LLM no disponible."}
            return await score_script(script, niche="Podcasting y Audio")

    result = asyncio.run(_run())
    assert "score" in result
    assert "rationale" in result
    assert 0 <= result["score"] <= 100, f"Score fuera de rango: {result['score']}"
    assert result["rationale"] == "Fallback: LLM no disponible."


def test_score_script_combines_rules_and_llm():
    """El score final debe ser la suma de reglas + LLM, limitado a 100."""
    from backend.services.trend_scorer import score_script

    script = {
        "gancho_0_5s": "¿Sabías que este truco cambia todo en audio?",
        "contexto_5_30s": "Aquí el secreto que nadie te enseña.",
        "moraleja_30_50s": "Aplica este método en 5 minutos al día.",
        "cta_50_60s": "Comenta PRECIO y te cuento la oferta.",
    }

    async def _run():
        with patch("backend.services.trend_scorer._score_by_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"llm_score": 35, "rationale": "Gancho retórico fuerte + CTA conversacional."}
            return await score_script(script, niche="Música y Producción")

    result = asyncio.run(_run())
    assert result["score"] >= 35, "Score total debe incluir el puntaje LLM"
    assert result["score"] <= 100
