"""
test_audit_second_pass_resolutions.py

Pruebas unitarias para validar las resoluciones de la Segunda Pasada de Auditoría Técnica:
1. Robustecimiento de pool async DB y Celery task_acks_late=True.
2. Grafo conversacional de DMs en LangGraph (dm_graph.py & dm_response.py).
3. Bucle RUM de Auto-Aprendizaje 72h con Media Móvil Exponencial (EMA) y clamp guardia [0.50, 0.90].
4. Verificación de aislamiento anti-IDOR en leads.py (Rechazo de acceso cruzado 403).
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from workers.celery_app import celery_app
from agents.nodes.dm_response import classify_intent, generate_grounded_reply, node_dm_response
from agents.dm_graph import build_dm_graph, route_after_dm_response
from agents.criterion.rum_calculator import get_dynamic_threshold
from workers.metrics_loop_task import update_niche_rum_threshold_ema, audit_72h_metrics
from backend.routers.leads import _verify_tenant_access_fail_closed


def test_celery_acks_late_configuration():
    """Verifica que Celery tenga activado task_acks_late y task_reject_on_worker_lost."""
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_anti_idor_unit_verified_user_mismatch():
    """
    Test unitario: verifica que _verify_tenant_access_fail_closed rechace cuando
    el usuario autenticado es de un tenant distinto al de la URL (tenant-B != tenant-A).
    En AGENCY_ENV=dev se omite la exigencia de authenticated_user para permitir testing local.
    """
    scope = {"type": "http", "method": "GET", "path": "/api/v1/tenants/tenant-A/leads", "headers": []}
    request = Request(scope)
    # Simular usuario JWT autenticado del tenant-B intentando acceder a tenant-A
    request.state.authenticated_user = {"sub": "user-B", "tenant_id": "tenant-B", "role": "editor"}
    request.state.tenant_id = "tenant-B"

    with pytest.raises(HTTPException) as exc_info:
        _verify_tenant_access_fail_closed(request, "tenant-A")

    assert exc_info.value.status_code == 403
    assert "Aislamiento Anti-IDOR violado" in exc_info.value.detail


def test_anti_idor_e2e_no_jwt_rejected():
    """
    Test de integración end-to-end (TestClient contra la app real):
    Verifica que GET /tenants/tenant-A/leads sin JWT válido y con
    X-Tenant-ID: tenant-B devuelva 401 o 403 (nunca 200 con datos de otro tenant).
    """
    import os
    from backend.main import app
    from fastapi.testclient import TestClient

    os.environ["AGENCY_ENV"] = "dev"

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/api/v1/tenants/tenant-A/leads",
        headers={"X-Tenant-ID": "tenant-B"},
    )

    assert response.status_code in (401, 403), (
        f"Se esperaba 401 o 403, pero se recibió {response.status_code} — posible IDOR activo."
    )


def test_anti_idor_e2e_real_jwt_cross_tenant():
    """
    Test e2e con JWT real firmado (recomendación fuerte pre-producción):
    Crea un token JWT auténtico con create_access_token para tenant-B,
    lo envía via Authorization: Bearer contra /tenants/tenant-A/leads,
    y verifica que verify_tenant_access (dependencia sistémica) lo rechace con 403.

    Este test ejerce el flujo completo en AGENCY_ENV=dev:
    middleware (extrae tenant-B del JWT) → verify_tenant_access (tenant-B != tenant-A) → 403.
    """
    import os
    from backend.main import app
    from backend.security.auth import create_access_token
    from fastapi.testclient import TestClient

    os.environ["AGENCY_ENV"] = "dev"

    # JWT real firmado con HMAC-SHA256 para tenant-B
    token_tenant_b = create_access_token(
        user_id="user-B-real", tenant_id="tenant-B", role="editor"
    )

    client = TestClient(app, raise_server_exceptions=False)

    # Intento de acceder a datos de tenant-A usando JWT de tenant-B
    response = client.get(
        "/api/v1/tenants/tenant-A/leads",
        headers={"Authorization": f"Bearer {token_tenant_b}"},
    )

    assert response.status_code == 403, (
        f"JWT de tenant-B debería recibir 403 al pedir datos de tenant-A, "
        f"pero se recibió {response.status_code}."
    )


def test_dm_intent_classification():
    """Verifica la clasificación de intenciones en mensajes de DM."""
    assert classify_intent("Hola, quiero comprar el sistema SaaS") == "purchase_intent"
    assert classify_intent("Tengo una duda, es muy caro?") == "objection"
    assert classify_intent("Donde puedo ver mas informacion?") == "question"
    assert classify_intent("Ganar crypto gratis http://link") == "spam"


@pytest.mark.anyio
async def test_dm_grounded_reply_confidence():
    """Verifica el cálculo del score de confianza en respuestas RAG (crew async)."""
    reply, conf = await generate_grounded_reply("¿Cómo funciona?", "Nuestro software automatiza el marketing...")
    assert conf >= 0.75

    reply_fail, conf_fail = await generate_grounded_reply("Pregunta desconocida", "no se encontro informacion")
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
    new_thresh = update_niche_rum_threshold_ema(niche, actual_engagement_ratio=15.0)
    assert 0.50 <= new_thresh <= 0.90

    thresh = get_dynamic_threshold(niche)
    assert 0.50 <= thresh <= 0.90

    audit_res = audit_72h_metrics.run(tenant_id="tenant-rum-test", video_id="v-100", views=20000, followers=1000, niche=niche)
    assert audit_res["classification"] == "VERDE"
    assert "recalibrated_rum_threshold" in audit_res
