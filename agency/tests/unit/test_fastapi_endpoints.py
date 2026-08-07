"""
test_fastapi_endpoints.py

Pruebas de integración con httpx para el servidor FastAPI main.py.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.anyio
async def test_create_tenant_endpoint():
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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/tenants/tenant-demo-001/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "classification" in data[0]


@pytest.mark.anyio
async def test_takeover_lead_endpoint():
    """Testa el endpoint de takeover. Sin DB disponible en test, espera 503 (no 200 con datos ficticios)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/tenants/tenant-demo-001/leads/lead-001/takeover",
            json={"operator_id": "admin_uuid_443", "action": "pause_bot"},
        )
    # 503 = sin DB disponible (comportamiento correcto); 200 = DB conectada (en staging/prod)
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "handled_by_human"
