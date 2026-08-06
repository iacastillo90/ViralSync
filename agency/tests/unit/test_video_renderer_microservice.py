"""
test_video_renderer_microservice.py

Pruebas unitarias para el microservicio de renderizado faceless (app.py) y el Agente Director (video_director_crew.py).
"""

import os
from agents.crews.video_director_crew import run_video_director_crew, extract_keywords_from_script
from workers.video_edit_task import trigger_video_render


def test_video_director_crew_payload_formatting():
    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
        "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
        "cta_50_60s": "Comenta SISTEMA abajo.",
        "keyword": "SISTEMA",
    }
    idea = {"texto": "Automatización Empresarial B2B"}

    director_res = run_video_director_crew(script=script, idea=idea, tenant_id="tenant-director-test")

    assert director_res["approved_for_render"] is True
    assert director_res["quality_score"] >= 0.70
    render_payload = director_res["render_payload"]
    assert "Automatización Empresarial B2B" in render_payload["title"]
    assert "3 errores fatales" in render_payload["script_text"]
    assert "Comenta SISTEMA" in render_payload["script_text"]
    assert isinstance(render_payload["keywords"], list)
    assert len(render_payload["keywords"]) > 0
    assert render_payload["tenant_id"] == "tenant-director-test"


def test_extract_keywords_from_script():
    keywords = extract_keywords_from_script("Texto de prueba para automatización de marketing", "Inteligencia Artificial SaaS")
    assert isinstance(keywords, list)
    assert len(keywords) <= 4
    assert "business" in keywords or "inteligencia" in keywords


def test_trigger_video_render_task_fallback():
    good_script = {
        "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
        "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
        "cta_50_60s": "Comenta la palabra DEMO abajo y te enviamos el desglose.",
        "keyword": "DEMO",
    }
    result = trigger_video_render.run(tenant_id="tenant-task-test", script=good_script)

    assert result["status"] == "completed"
    assert "video_url" in result
    assert result["tenant_id"] == "tenant-task-test"
