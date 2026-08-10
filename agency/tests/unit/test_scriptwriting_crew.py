"""
test_scriptwriting_crew.py

Pruebas unitarias TDD para la Crew de Guionismo en 4 Bloques (CrewAI).
"""

import asyncio
import json

from agents.crews import scriptwriting_crew
from agents.crews.scriptwriting_crew import run_scriptwriting_crew

LLM_SCRIPT_JSON = json.dumps({
    "gancho_0_5s": "GANCHO LLM",
    "contexto_5_30s": "CONTEXTO LLM",
    "moraleja_30_50s": "MORALEJA LLM",
    "cta_50_60s": "CTA LLM",
    "keyword": "CONSULTA",
})


def test_run_scriptwriting_crew_4_blocks():
    idea = {
        "texto": "3 Errores Críticos al Escalar B2B",
        "gancho": "Si trabajas en B2B, escucha esto",
        "rum_score": 0.444,
    }
    ppp = "Consigue 100 clientes en 30 días sin anuncios"

    script = asyncio.run(run_scriptwriting_crew(idea, niche_ppp=ppp))
    
    assert "gancho_0_5s" in script
    assert "contexto_5_30s" in script
    assert "moraleja_30_50s" in script
    assert "cta_50_60s" in script
    assert "keyword" in script
    assert script["keyword"]  # Verificar que no esté vacío
    assert script["keyword"].upper() in script["cta_50_60s"].upper()


def test_run_scriptwriting_crew_injects_rum_threshold_and_trends(monkeypatch):
    # CVD-03-1 + CVD-04-1: prompt seam carries the Redis RUM threshold (0.78)
    # and the sanitized trend section when both are present.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_SCRIPT_JSON

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        scriptwriting_crew, "resolve_rum_threshold", lambda niche: 0.78
    )
    monkeypatch.setattr(
        scriptwriting_crew, "build_trend_section", lambda niche: "- Reels virales B2B 2026"
    )

    idea = {
        "texto": "3 Errores Críticos al Escalar B2B",
        "gancho": "Si trabajas en B2B, escucha esto",
        "rum_score": 0.444,
        "niche": "B2B Marketing",
    }

    script = asyncio.run(run_scriptwriting_crew(idea, niche_ppp="ppp"))

    assert script["keyword"] == "CONSULTA"  # LLM path ran -> seam executed
    assert "0.78" in calls["user_prompt"]  # CVD-03-1
    assert "Reels virales B2B 2026" in calls["user_prompt"]  # CVD-04-1


def test_run_scriptwriting_crew_absent_context_non_fatal(monkeypatch):
    # CVD-03-2 + CVD-04-2: Redis down / cache miss -> clamp default injected,
    # trend section omitted, crew still produces its output.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_SCRIPT_JSON

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        scriptwriting_crew, "resolve_rum_threshold", lambda niche: 0.70
    )
    monkeypatch.setattr(scriptwriting_crew, "build_trend_section", lambda niche: "")

    idea = {
        "texto": "3 Errores Críticos al Escalar B2B",
        "gancho": "Si trabajas en B2B, escucha esto",
        "rum_score": 0.444,
        "niche": "B2B Marketing",
    }

    script = asyncio.run(run_scriptwriting_crew(idea, niche_ppp="ppp"))

    assert script["keyword"] == "CONSULTA"  # crew still outputs
    assert "0.70" in calls["user_prompt"]  # CVD-03-2 clamp default injected
    assert "Trending topics" not in calls["user_prompt"]  # CVD-04-2 omitted
