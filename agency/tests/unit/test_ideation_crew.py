"""
test_ideation_crew.py

Pruebas unitarias TDD para la Crew de Ideación (CrewAI).
"""

import json

from agents.crews.ideation_crew import run_ideation_crew


def test_run_ideation_crew_structure():
    niche = "Negocios B2B y SaaS"
    market_map = {
        "errores": ["Falta de tracción"],
        "deseos": ["Escalar ventas"],
    }
    
    ideas = run_ideation_crew(niche, market_map)
    
    assert isinstance(ideas, list)
    assert len(ideas) >= 1
    
    for idea in ideas:
        assert "texto" in idea
        assert "gancho" in idea
        assert "rum_score" in idea
        assert idea["passes_5_50"] is True
        assert isinstance(idea["rum_score"], float)


def test_ideation_uses_llm_text_when_provider_responds(monkeypatch):
    """LLM-02-2: si agents.llm responde, la crew usa el texto real y NO el fallback '3 Errores...'."""
    niche = "Kinesiología Deportiva"
    market_map = {
        "errores": ["Falta de pacientes recurrentes"],
        "deseos": ["Llenar agenda semanal"],
    }

    llm_text = json.dumps(
        [
            {
                "texto": "TITULO REAL GENERADO POR EL LLM",
                "gancho": "Gancho real del LLM",
                "entendible_nino_5_anos": True,
                "interesa_50_de_100": True,
                "universalidad": 0.85,
                "intensidad": 0.90,
                "claridad": 0.95,
                "shareability": 0.80,
                "distribucion": 0.85,
                "alineacion": 0.90,
            }
        ],
        ensure_ascii=False,
    )

    def fake_complete(messages, temperature=0.7, max_tokens=1000, **kwargs):
        # La crew preserva la temperatura y max_tokens del call site (design D1).
        assert temperature == 0.7
        assert max_tokens == 1000
        assert messages[0]["role"] == "system"
        return llm_text

    monkeypatch.setattr("agents.llm.complete", fake_complete)

    ideas = run_ideation_crew(niche, market_map)

    assert len(ideas) >= 1
    assert ideas[0]["texto"] == "TITULO REAL GENERADO POR EL LLM"
    assert all("3 Errores" not in idea.get("texto", "") for idea in ideas)
