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


def _auth_header(tenant_id: str, role: str = "admin") -> dict:
    """Helper: genera JWT real para el tenant dado y devuelve el header de Authorization."""
    token = create_access_token(user_id=f"user-test-{tenant_id}", tenant_id=tenant_id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_create_tenant_endpoint():
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
async def test_get_metrics_endpoint():
    """Accede a /metrics con JWT válido del mismo tenant. Sin DB → lista vacía."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/tenants/tenant-demo-001/metrics",
            headers=_auth_header("tenant-demo-001"),
        )
    # Sin DB en entorno de test: lista vacía (correcto); con DB: lista de métricas reales
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


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
async def test_create_tenant_no_jwt_required():
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
