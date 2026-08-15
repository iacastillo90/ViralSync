"""
test_fastapi_endpoints.py

Pruebas de integración con httpx para el servidor FastAPI main.py.
Todos los endpoints bajo /tenants/{tenant_id} requieren JWT válido
(verify_tenant_access aplicado sistémicamente en include_router).
POST /api/v1/tenants es endpoint público de registro (sin guard).
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.security.auth import create_access_token
from backend.db.models import Tenant, VideoMetric, Lead


def _auth_header(tenant_id: str, role: str = "admin") -> dict:
    """Helper: genera JWT real para el tenant dado y devuelve el header de Authorization."""
    token = create_access_token(user_id=f"user-test-{tenant_id}", tenant_id=tenant_id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_create_tenant_endpoint(init_test_db):
    """POST /api/v1/tenants es público (registro de nuevo tenant) — no requiere JWT."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tenants",
            json={
                "name": "Cliente Demo Marketing",
                "niche": "Negocios B2B y SaaS",
                "monthly_llm_budget_usd": 20.00,
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "litellm_virtual_key" in data


@pytest.mark.anyio
async def test_get_metrics_endpoint(init_test_db):
    """Accede a /metrics con JWT válido del mismo tenant. 200-only (REQ-VID-2 / API-04-1)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/tenants/tenant-demo-001/metrics",
            headers=_auth_header("tenant-demo-001"),
        )
    assert response.status_code == 200, (
        f"/metrics no debe 503 con DB sana — recibió {response.status_code}"
    )
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_get_metrics_flat_shape_no_metrics_72h_nesting(db_session):
    """REQ-API-4 (API-04-2): una fila video_metrics devuelve el shape plano de la DDL 002."""
    tenant_id = "7f9e4c2a-1b3d-4e5f-8a9b-0c1d2e3f4a5b"
    db_session.add(Tenant(id=tenant_id, name="Flat Metrics Tenant"))
    await db_session.commit()

    db_session.add(
        VideoMetric(
            id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
            tenant_id=tenant_id,
            video_id="11111111-aaaa-4bbb-8ccc-000000000001",
            views_72h=100,
            likes=40,
            comments=10,
            shares=5,
            ratio_relativo=2.5,
            classification="VERDE",
            action_taken="Generar 3 variaciones",
        )
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tenants/{tenant_id}/metrics",
            headers=_auth_header(tenant_id),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    item = body[0]
    assert item["video_id"] == "11111111-aaaa-4bbb-8ccc-000000000001"
    assert item["views_72h"] == 100
    assert item["likes"] == 40
    assert item["comments"] == 10
    assert item["shares"] == 5
    assert item["ratio_relativo"] == 2.5
    assert item["classification"] == "VERDE"
    assert item["action_taken"] == "Generar 3 variaciones"
    assert "captured_at" in item
    # El contrato legacy anidado y las columnas fantasma NO pueden volver
    assert "metrics_72h" not in item
    assert "published_at" not in item
    assert "views" not in item


@pytest.mark.anyio
async def test_get_metrics_72h_aggregates_ddl_002_columns(db_session):
    """REQ-VID-2: el agregado 72h suma/agrupa las columnas alineadas de la DDL 002."""
    tenant_id = "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f"
    db_session.add(Tenant(id=tenant_id, name="72h Tenant"))
    await db_session.commit()

    db_session.add_all(
        [
            VideoMetric(
                id="b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
                tenant_id=tenant_id,
                video_id="22222222-aaaa-4bbb-8ccc-000000000002",
                views_72h=100,
                likes=40,
                comments=10,
                shares=5,
                ratio_relativo=2.5,
                classification="VERDE",
                action_taken=None,
            ),
            VideoMetric(
                id="c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
                tenant_id=tenant_id,
                video_id="33333333-aaaa-4bbb-8ccc-000000000003",
                views_72h=50,
                likes=20,
                comments=7,
                shares=2,
                ratio_relativo=1.0,
                classification="AMARILLO",
                action_taken=None,
            ),
        ]
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tenants/{tenant_id}/metrics/72h",
            headers=_auth_header(tenant_id),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["tenant_id"] == tenant_id
    assert data["window_hours"] == 72
    metrics = data["metrics"]
    assert metrics["total_views"] == 150
    assert metrics["total_likes"] == 60
    assert metrics["total_comments"] == 17
    assert metrics["total_shares"] == 7
    assert metrics["avg_ratio_relativo"] == 1.75
    assert metrics["videos_analyzed"] == 2
    assert metrics["classification_distribution"] == {"ROJO": 0, "AMARILLO": 1, "VERDE": 1}


@pytest.mark.anyio
async def test_get_metrics_72h_empty_window_returns_no_data(db_session):
    """Sin métricas en la ventana → {"status": "no_data"} sin datos inventados."""
    tenant_id = "3d4e5f6a-7b8c-4d9e-0f1a-2b3c4d5e6f7a"
    db_session.add(Tenant(id=tenant_id, name="Empty 72h Tenant"))
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tenants/{tenant_id}/metrics/72h",
            headers=_auth_header(tenant_id),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_data"
    assert data["tenant_id"] == tenant_id
    assert data["window_hours"] == 72


@pytest.mark.anyio
async def test_takeover_lead_endpoint():
    """
    Testa el endpoint de takeover con JWT válido del mismo tenant.
    Sin DB disponible en test → 503 (explícito, no dato ficticio).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tenants/tenant-demo-001/leads/lead-001/takeover",
            json={"operator_id": "admin_uuid_443", "action": "pause_bot"},
            headers=_auth_header("tenant-demo-001"),
        )
    # 503 = sin DB disponible; 404 = DB conectada pero lead inexistente (correcto); 200 = DB conectada y lead existente
    assert response.status_code in (200, 404, 503)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "handled_by_human"


@pytest.mark.anyio
async def test_cross_tenant_metrics_rejected():
    """
    Verifica que JWT de tenant-intruso NO puede leer métricas de tenant-demo-001.
    Guard sistémico verify_tenant_access debe devolver 403.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/tenants/tenant-demo-001/metrics",
            headers=_auth_header("tenant-intruso"),
        )
    assert response.status_code == 403, (
        f"JWT de tenant-intruso debería recibir 403 al pedir datos de tenant-demo-001, "
        f"pero se recibió {response.status_code}."
    )


@pytest.mark.anyio
async def test_create_tenant_no_jwt_required(init_test_db):
    """POST /api/v1/tenants no exige JWT — cualquier request sin Authorization debe pasar."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tenants",
            json={"name": "Nuevo Cliente", "niche": "Fitness", "monthly_llm_budget_usd": 15.0},
            # Sin header de Authorization
        )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_list_tenants_returns_only_safe_public_fields(init_test_db, db_session):
    """GET /api/v1/tenants list dev NO expone campos sensibles por tenant (R1-002)."""
    public_a = "cafe0001-0000-4000-8000-000000000001"
    public_b = "cafe0001-0000-4000-8000-000000000002"
    db_session.add(Tenant(id=public_a, name="Publico A", niche="SaaS"))
    db_session.add(Tenant(id=public_b, name="Publico B", niche="Gyms"))
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/tenants")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    # La shared-DB de la sesión pytest acumula tenants de otros tests: solo
    # verificamos que NUESTROS tenants estén presentes y que NINGÚN item
    # exponga campos internos (independiente del conteo total).
    ids = {item["id"] for item in body}
    assert public_a in ids and public_b in ids
    for item in body:
        assert set(item.keys()) == {"id", "name", "niche"}, (
            f"El listado de tenants NO debe exponer campos internos, recibió keys={set(item.keys())}"
        )


@pytest.mark.anyio
async def test_get_tenant_detail_requires_own_jwt(init_test_db):
    """GET /api/v1/tenants/{id} exige aislamiento Anti-IDOR (R1-002): JWT del mismo tenant."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        # Crear tenant vía flujo real (registro público) para tener un UUID/DB válida.
        created = await ac.post(
            "/api/v1/tenants",
            json={"name": "Detail Tenant", "niche": "Fitness", "monthly_llm_budget_usd": 30.0},
        )
        assert created.status_code == 201
        tenant_id = created.json()["id"]

        # JWT del MISMO tenant -> 200 y detalle visible
        own = await ac.get(
            f"/api/v1/tenants/{tenant_id}",
            headers=_auth_header(tenant_id),
        )
        assert own.status_code == 200, f"JWT propio debe ver el detalle, recibió {own.status_code}"
        detail = own.json()
        assert detail["id"] == tenant_id
        assert detail["name"] == "Detail Tenant"
        assert "litellm_virtual_key" not in detail

        # JWT de OTRO tenant -> 403 (aislamiento Anti-IDOR en detalle)
        intruder = await ac.get(
            f"/api/v1/tenants/{tenant_id}",
            headers=_auth_header("tenant-intruso"),
        )
        assert intruder.status_code == 403, (
            f"JWT de otro tenant NO puede ver el detalle, recibió {intruder.status_code}"
        )


@pytest.mark.anyio
async def test_get_leads_exposes_scoring_fields(db_session):
    """T-S1-08: GET /{tenant}/leads expone qualification_score, status e intent (S1)."""
    import uuid as _uuid

    tenant_id = "4e5f6a7b-8c9d-4e0f-1a2b-3c4d5e6f7a8b"
    db_session.add(Tenant(id=tenant_id, name="Scoring Tenant S1"))
    await db_session.commit()

    db_session.add(
        Lead(
            id=str(_uuid.uuid4()),
            tenant_id=tenant_id,
            video_id=None,
            keyword="AUDIO",
            ig_user_id="user_score_1",
            mensaje_original="Quiero comprar el sistema con AUDIO por favor",
            origen="comment",
            status="Calificado",
            qualification_score=90,
            platform="instagram",
            dedup_hash="hash-score-s1",
            conversacion_history=(
                '[{"intent": "purchase_intent", "confidence": 0.92, "ts": "2026-01-01T00:00:00"}]'
            ),
        )
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tenants/{tenant_id}/leads",
            headers=_auth_header(tenant_id),
        )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) == 1
    row = data[0]
    assert row["qualification_score"] == 90
    assert row["status"] == "Calificado"
    assert row["intent"] == "purchase_intent"
