"""
test_ideation_crew.py

Pruebas unitarias TDD para la Crew de Ideación (CrewAI).
"""

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
