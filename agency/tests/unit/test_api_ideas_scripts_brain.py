"""
test_api_ideas_scripts_brain.py

Integration tests (httpx ASGITransport) for the slice-1 backend contracts:

Auth guard (REQ-API-05):
- dev real-UUID GET returns 200 without JWT (API-05-1)
- prod without JWT returns 401 — AGENCY_ENV must be monkeypatched as the
  MODULE constant backend.security.auth.AGENCY_ENV, never only os.environ,
  because it is read at import time (API-05-2)
- dev cross-tenant (header=B, URL=A) still 403 (API-05-3)

New GET endpoints (REQ-API-1/2/3, added in another unit of this slice) are
extended in this same file.
"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.security.auth import create_access_token
import backend.security.auth as auth_module


def _auth_header(tenant_id: str, role: str = "admin") -> dict:
    """Helper: JWT real para el tenant dado, del mismo estilo que test_fastapi_endpoints."""
    token = create_access_token(user_id=f"user-test-{tenant_id}", tenant_id=tenant_id, role=role)
    return {"Authorization": f"Bearer {token}"}


# URL-tenant y header-tenant diferenciados para el escenario cross-tenant
TENANT_A = "d20d01be-9267-44d4-a985-aa45e36c4648"
TENANT_B = "83b8444c-f296-496a-9683-93eb5fa948d7"


@pytest.mark.anyio
async def test_dev_real_uuid_get_returns_200_without_jwt(init_test_db):
    """API-05-1: en dev, sin JWT y con un tenant UUID real en la URL → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/metrics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_prod_without_jwt_returns_401(init_test_db, monkeypatch):
    """API-05-2: en producción el fallback NO existe — sin JWT → 401.

    CRITICAL: se parchea la CONSTANTE DE MÓDULO backend.security.auth.AGENCY_ENV,
    no os.environ (auth.py:22 la lee en el import; no se re-lee en request-time).
    """
    monkeypatch.setattr(auth_module, "AGENCY_ENV", "prod")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/metrics")
    assert response.status_code == 401, f"prod sin JWT debe ser 401, recibió {response.status_code}"


@pytest.mark.anyio
async def test_prod_without_jwt_401_for_other_get_endpoints(init_test_db, monkeypatch):
    """API-05-2 aplicado a los GET pendientes: /leads también fail-closed en prod."""
    monkeypatch.setattr(auth_module, "AGENCY_ENV", "prod")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/leads")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_dev_cross_tenant_header_b_url_a_returns_403(init_test_db):
    """API-05-3: header X-Tenant-ID=B con URL tenant=A → 403 incluso en dev."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{TENANT_A}/metrics",
            headers={"X-Tenant-ID": TENANT_B},
        )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_dev_jwt_of_tenant_b_cannot_read_tenant_a(init_test_db):
    """API-GET-4: JWT del tenant B pedido sobre la URL del tenant A → 403 (anti-IDOR)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{TENANT_A}/metrics",
            headers=_auth_header(TENANT_B),
        )
    assert response.status_code == 403