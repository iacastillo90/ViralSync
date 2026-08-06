"""
test_video_renderer_microservice.py

Pruebas unitarias para el microservicio de renderizado faceless (app.py) y el Agente Director (video_director_crew.py).
"""

import os
from agents.crews.video_director_crew import run_video_director_crew, extract_keywords_from_script
from workers.video_edit_task import trigger_video_render


def test_video_director_crew_payload_formatting():
    script = {
        "gancho_0_5s": "El mayor error al escalar tu negocio.",
        "contexto_5_30s": "Intentar hacer todo manualmente sin automatización.",
        "moraleja_30_50s": "Implementa sistemas automatizados con IA.",
        "cta_50_60s": "Comenta SISTEMA abajo.",
        "keyword": "SISTEMA",
    }
    idea = {"texto": "Automatización Empresarial B2B"}

    payload = run_video_director_crew(script=script, idea=idea, tenant_id="tenant-director-test")

    assert payload["title"] == "Automatización Empresarial B2B"
    assert "El mayor error al escalar" in payload["script_text"]
    assert "Comenta SISTEMA" in payload["script_text"]
    assert isinstance(payload["keywords"], list)
    assert len(payload["keywords"]) > 0
    assert payload["tenant_id"] == "tenant-director-test"


def test_extract_keywords_from_script():
    keywords = extract_keywords_from_script("Texto de prueba para automatización de marketing", "Inteligencia Artificial SaaS")
    assert isinstance(keywords, list)
    assert len(keywords) <= 4
    assert "business" in keywords or "inteligencia" in keywords


def test_trigger_video_render_task_fallback():
    script = {
        "gancho_0_5s": "3 Secretos de Marketing",
        "contexto_5_30s": "Aplica estrategias basadas en datos",
        "moraleja_30_50s": "Revisa tus métricas",
        "cta_50_60s": "Comenta REEL",
    }
    result = trigger_video_render.run(tenant_id="tenant-task-test", script=script)

    assert result["status"] == "completed"
    assert "video_url" in result
    assert result["tenant_id"] == "tenant-task-test"
