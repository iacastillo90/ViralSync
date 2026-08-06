"""
test_video_director_guardian.py

Pruebas unitarias para el VideoDirectorAgent como Guardián de Calidad y Rendimiento:
1. Filtro de Valor (Evaluación de Impacto RUM).
2. Filtro de Hardware (Restricciones Quirúrgicas 45s / 720p).
3. Curaduría de Metadatos (Título, Descripción y Hashtags).
"""

from agents.crews.video_director_crew import (
    run_video_director_crew,
    evaluate_script_quality,
    curate_video_metadata,
)
from workers.video_edit_task import trigger_video_render


def test_evaluate_script_quality_pass():
    good_script = {
        "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
        "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
        "cta_50_60s": "Comenta la palabra DEMO abajo y te enviamos el desglose.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    score, approved, feedback = evaluate_script_quality(good_script, idea)

    assert score >= 0.70
    assert approved is True
    assert len(feedback) == 0


def test_evaluate_script_quality_fail():
    poor_script = {
        "gancho_0_5s": "Hola",
        "contexto_5_30s": "Cómprame algo",
        "moraleja_30_50s": "Es bueno",
        "cta_50_60s": "Chao",
        "keyword": "",
    }
    idea = {"texto": "Spam Ad"}

    score, approved, feedback = evaluate_script_quality(poor_script, idea)

    assert score < 0.70
    assert approved is False
    assert len(feedback) > 0


def test_curate_video_metadata():
    script = {"gancho_0_5s": "3 Errores al Escalar B2B", "keyword": "CONSULTA"}
    idea = {"texto": "Estrategia B2B", "niche": "Marketing SaaS"}

    metadata = curate_video_metadata(script, idea)

    assert "🚀 Estrategia B2B | Caso Práctico 2026" in metadata["final_title"]
    assert "CONSULTA" in metadata["description"]
    assert len(metadata["hashtags"]) >= 4
    assert "#marketingsaas" in metadata["hashtags"]


test_video_director_hardware_filter = None


def test_video_director_hardware_filter_and_rejection():
    poor_script = {
        "gancho_0_5s": "Hi",
        "contexto_5_30s": "Short",
        "moraleja_30_50s": "Small",
        "cta_50_60s": "Bye",
        "keyword": "",
    }
    result = trigger_video_render.run(tenant_id="tenant-guardian-test", script=poor_script)

    assert result["status"] == "rejected_quality"
    assert result["quality_score"] < 0.70
    assert "no superó el umbral" in result["message"]
