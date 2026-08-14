"""
test_ideation_crew.py

Pruebas unitarias para la Crew de Ideación (validación estricta de exactamente 5 ideas).

Escenarios cubiertos:
- Respuesta con exactamente 5 ideas → pasa sin reintentos.
- Respuesta con 1 idea → reintenta y finalmente lanza NoCandidatesError.
- Respuesta que recién en el tercer intento trae 5 ideas → reintenta y pasa.
- JSON mal formado en todos los intentos → NoCandidatesError.
- LLM caído (excepción/rate-limit) → fallback dinámico genera exactamente 5 ideas.
- El filtro 5/50 descarta candidatas → se completan hasta 5 con las de mayor RUM.
"""

import asyncio
import json

import pytest

from agents.crews.ideation_crew import run_ideation_crew
from agents.errors import NoCandidatesError


def _build_idea(texto, gancho, entendible=True, interesa=True):
    return {
        "texto": texto,
        "gancho": gancho,
        "entendible_nino_5_anos": entendible,
        "interesa_50_de_100": interesa,
        "universalidad": 0.85,
        "intensidad": 0.90,
        "claridad": 0.95,
        "shareability": 0.80,
        "distribucion": 0.85,
        "alineacion": 0.90,
    }


def _build_five_ideas():
    return [_build_idea(f"IDEA {i}", f"Gancho {i}") for i in range(5)]


def _json_response(ideas):
    return json.dumps(ideas, ensure_ascii=False)


@pytest.fixture(autouse=True)
def _mock_trends(monkeypatch):
    """Evita cualquier llamada real a SearXNG: los tests son deterministas y sin red."""

    async def fake_searxng(query, num_results=3):
        return []

    monkeypatch.setattr(
        "agents.crews.ideation_crew.asearxng_search_sanitized", fake_searxng
    )


def test_run_ideation_crew_structure():
    niche = "Negocios B2B y SaaS"
    market_map = {
        "errores": ["Falta de tracción"],
        "deseos": ["Escalar ventas"],
    }

    ideas = asyncio.run(run_ideation_crew(niche, market_map))

    assert isinstance(ideas, list)
    assert len(ideas) == 5

    for idea in ideas:
        assert "texto" in idea
        assert "gancho" in idea
        assert "rum_score" in idea
        assert idea["passes_5_50"] is True
        assert isinstance(idea["rum_score"], float)


def test_ideation_uses_llm_text_when_provider_responds(monkeypatch):
    """Si agents.llm responde con 5 ideas, la crew usa el texto real y NO el fallback."""
    niche = "Kinesiología Deportiva"
    market_map = {
        "errores": ["Falta de pacientes recurrentes"],
        "deseos": ["Llenar agenda semanal"],
    }

    llm_text = _json_response(
        [
            _build_idea(f"TITULO REAL {i}", f"Gancho real del LLM {i}") for i in range(5)
        ]
    )

    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        # La crew preserva la temperatura y max_tokens del call site (design D1)
        # y llama al seam ASYNC (RELIABILITY-003): nunca complete() síncrono.
        assert temperature == 0.7
        assert max_tokens == 8192
        assert messages[0]["role"] == "system"
        return llm_text

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    ideas = asyncio.run(run_ideation_crew(niche, market_map))

    assert len(ideas) == 5
    assert ideas[0]["texto"] == "TITULO REAL 0"
    assert all("3 Errores" not in idea.get("texto", "") for idea in ideas)


def test_ideation_accepts_exactly_five_without_retry(monkeypatch):
    """Respuesta con exactamente 5 ideas → pasa en un solo intento."""
    calls = {"n": 0}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        calls["n"] += 1
        return _json_response(_build_five_ideas())

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    ideas = asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))

    assert len(ideas) == 5
    assert calls["n"] == 1


def test_ideation_single_idea_retries_and_raises(monkeypatch):
    """Respuesta con 1 sola idea → reintenta y, al no llegar a 5, lanza NoCandidatesError."""
    single = _json_response([_build_idea("IDEA ÚNICA", "Gancho único")])
    calls = {"n": 0}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        calls["n"] += 1
        return single

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    with pytest.raises(NoCandidatesError):
        asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))

    assert calls["n"] == 3


def test_ideation_retries_until_five(monkeypatch):
    """Recién el tercer intento trae 5 ideas → se reintenta y se acepta."""
    single = _json_response([_build_idea("IDEA ÚNICA", "Gancho único")])
    five = _json_response(_build_five_ideas())
    responses = iter([single, single, five])

    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        return next(responses)

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    ideas = asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))

    assert len(ideas) == 5
    assert ideas[0]["texto"] == "IDEA 0"


def test_ideation_malformed_json_raises(monkeypatch):
    """JSON mal formado en todos los intentos → NoCandidatesError (nunca menos de 5)."""
    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        return "respuesta sin JSON válido"

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    with pytest.raises(NoCandidatesError):
        asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))


def test_ideation_fallback_generates_five(monkeypatch):
    """LLM caído (excepción/rate-limit) → el fallback dinámico genera exactamente 5 ideas."""
    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        raise RuntimeError("rate-limit simulado")

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    ideas = asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))

    assert len(ideas) == 5
    for idea in ideas:
        assert idea["passes_5_50"] is True
        assert isinstance(idea["rum_score"], float)


def test_ideation_fills_to_five_after_filter(monkeypatch):
    """Si el filtro 5/50 descarta candidatas, se completan hasta 5 con las de mayor RUM."""
    ideas_payload = _build_five_ideas()
    # Las ideas 1 y 3 no pasan el filtro 5/50.
    ideas_payload[1]["entendible_nino_5_anos"] = False
    ideas_payload[3]["interesa_50_de_100"] = False
    # La idea 1 descartada tiene el mayor RUM posible y debe ocupar una vacante.
    for key in ("universalidad", "intensidad", "claridad", "shareability", "distribucion", "alineacion"):
        ideas_payload[1][key] = 1.0

    async def fake_acomplete(messages, temperature=0.7, max_tokens=8192, **kwargs):
        return _json_response(ideas_payload)

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)

    ideas = asyncio.run(run_ideation_crew("Kinesiología Deportiva", {"errores": [], "deseos": []}))

    assert len(ideas) == 5
    textos = [idea["texto"] for idea in ideas]
    assert "IDEA 1" in textos
    assert "IDEA 3" in textos
    for idea in ideas:
        assert idea["passes_5_50"] is True
