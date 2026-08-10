"""
test_scriptwriting_crew.py

Pruebas unitarias TDD para la Crew de Guionismo en 4 Bloques (CrewAI).
"""

import asyncio

from agents.crews.scriptwriting_crew import run_scriptwriting_crew


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
