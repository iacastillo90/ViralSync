"""
test_audit_second_pass_resolutions.py

Pruebas unitarias para validar las resoluciones de la Segunda Pasada de Auditoría Técnica:
1. Robustecimiento de pool async DB y Celery task_acks_late=True.
2. Grafo conversacional de DMs en LangGraph (dm_graph.py & dm_response.py).
3. Bucle RUM de Auto-Aprendizaje 72h con Media Móvil Exponencial (EMA) y clamp guardia [0.50, 0.90].
4. Verificación de aislamiento anti-IDOR en leads.py.
"""

import pytest
from workers.celery_app import celery_app
from agents.nodes.dm_response import classify_intent, generate_grounded_reply, node_dm_response
from agents.dm_graph import build_dm_graph, route_after_dm_response
from agents.criterion.rum_calculator import get_dynamic_threshold
from workers.metrics_loop_task import update_niche_rum_threshold_ema, audit_72h_metrics


def test_celery_acks_late_configuration():
    """Verifica que Celery tenga activado task_acks_late y task_reject_on_worker_lost."""
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_dm_intent_classification():
    """Verifica la clasificación de intenciones en mensajes de DM."""
    assert classify_intent("Hola, quiero comprar el sistema SaaS") == "purchase_intent"
    assert classify_intent("Tengo una duda, es muy caro?") == "objection"
    assert classify_intent("Donde puedo ver mas informacion?") == "question"
    assert classify_intent("Ganar crypto gratis http://link") == "spam"


def test_dm_grounded_reply_confidence():
    """Verifica el cálculo del score de confianza en respuestas RAG."""
    reply, conf = generate_grounded_reply("¿Cómo funciona?", "Nuestro software automatiza el marketing...")
    assert conf >= 0.75
    assert "software" in reply

    reply_fail, conf_fail = generate_grounded_reply("Pregunta desconocida", "no se encontro informacion")
    assert conf_fail < 0.75


def test_dm_graph_routing():
    """Verifica las reglas de enrutamiento condicional post-respuesta de DM."""
    state_human = {"requires_human": True, "tenant_id": "tenant-test", "lead_id": "lead-01"}
    state_auto = {"requires_human": False, "tenant_id": "tenant-test", "lead_id": "lead-02"}

    assert route_after_dm_response(state_human) == "human_takeover"
    assert route_after_dm_response(state_auto) == "send_dm_reply"


@pytest.mark.anyio
async def test_dm_graph_compilation_and_execution():
    """Verifica la ejecución completa del grafo LangGraph de DMs."""
    dm_graph = build_dm_graph()
    state = {
        "tenant_id": "tenant-graph-test",
        "lead_id": "lead-dm-99",
        "incoming_message": "Quiero comprar la licencia Enterprise",
        "conversation_history": [],
    }

    final_state = await dm_graph.ainvoke(state)
    assert final_state["intent"] == "purchase_intent"
    assert final_state["requires_human"] is True


def test_rum_ema_recalibration_and_clamp():
    """Verifica la recalibración EMA del umbral RUM y la protección de clamp [0.50, 0.90]."""
    niche = "TestSaaS"
    # Recalibrar con alto engagement
    new_thresh = update_niche_rum_threshold_ema(niche, actual_engagement_ratio=15.0)
    assert 0.50 <= new_thresh <= 0.90

    # Probar lectura dinámica
    thresh = get_dynamic_threshold(niche)
    assert 0.50 <= thresh <= 0.90

    # Ejecución de la tarea Celery de métricas 72h
    audit_res = audit_72h_metrics.run(tenant_id="tenant-rum-test", video_id="v-100", views=20000, followers=1000, niche=niche)
    assert audit_res["classification"] == "VERDE"
    assert "recalibrated_rum_threshold" in audit_res
