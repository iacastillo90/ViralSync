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
from sqlalchemy import text

from backend.main import app
from backend.security.auth import create_access_token
from backend.db.models import Idea, Niche, Script, Tenant
import backend.security.auth as auth_module


def _auth_header(tenant_id: str, role: str = "admin") -> dict:
    """Helper: JWT real para el tenant dado, del mismo estilo que test_fastapi_endpoints."""
    token = create_access_token(user_id=f"user-test-{tenant_id}", tenant_id=tenant_id, role=role)
    return {"Authorization": f"Bearer {token}"}


# URL-tenant y header-tenant diferenciados para el escenario cross-tenant
TENANT_A = "d20d01be-9267-44d4-a985-aa45e36c4648"
TENANT_B = "83b8444c-f296-496a-9683-93eb5fa948d7"
# Tenant dedicado para el test del brain con persona (evita colisión UNIQUE
# de tenants.id con el db_session compartido a nivel de sesión)
TENANT_BRAIN = "9a3f4d2c-1e5b-4c7a-8f2d-6b8e9c0a1d2e"

# IDs de filas en espacio propio de este archivo (prefijo aaaa…) — el motor
# SQLite en memoria se comparte para TODA la sesión de pytest (StaticPool,
# conftest.py), así que cualquier UUID repetido entre archivos de test rompe
# UNIQUE constraints. test_video_metric_orm_alignment.py usa 1111/3333/…,
# test_enterprise_phases_0_to_5.py usa los suyos; este archivo usa el suyo.
IDEA_TEST_ID = "aaaa0001-5555-6666-7777-888888888888"
SCRIPT_TEST_ID = "aaaa0002-5555-6666-7777-888888888888"
NICHE_TEST_ID = "aaaa0003-5555-6666-7777-888888888888"


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


# --------------------------------------------------------------------------- #
# Nuevos GETs: /ideas, /scripts, /brain (REQ-API-1/2/3)
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_dev_ideas_returns_200_empty_list(init_test_db):
    """REQ-API-1 (API-GET-1): ideas sin filas → 200 [] (nunca 404)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/ideas")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_dev_scripts_returns_200_empty_list(init_test_db):
    """REQ-API-2 (API-02-1): scripts sin filas → 200 []."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/scripts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_dev_brain_returns_honest_object(init_test_db):
    """REQ-API-3 (API-03-1/2): brain fabrica-free — objeto, chunks [], sin '1240'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/brain")
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == TENANT_A
    assert body["status"] == "no_data"
    assert body["persona"] is None
    assert body["collection_stats"] is None
    assert body["chunks"] == []
    assert body["collection"] == "marketing_brain"
    assert "1240" not in response.text


@pytest.mark.anyio
async def test_ideas_rows_expose_ddl_001_shape(db_session):
    """REQ-API-1 (API-GET-2): una fila real → 200 con todos los keys del DDL 001."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Seed tenant + idea con las columnas del DDL real
        from backend.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as ses:
            ses.add(Tenant(id=TENANT_A, name="Ideas Tenant"))
            await ses.commit()
            ses.add(
                Idea(
                    id=IDEA_TEST_ID,
                    tenant_id=TENANT_A,
                    texto="Escalar SaaS con contenido B2B",
                    gancho="¿Tu equipo vende sin contenido?",
                    entendible_nino_5_anos=True,
                    interesa_50_de_100=True,
                    universalidad=0.9,
                    intensidad=0.8,
                    claridad=0.7,
                    shareability=0.6,
                    distribucion=0.5,
                    alineacion=0.9,
                    rum_score=0.444,
                    passes_threshold=True,
                    approval_status="pending",
                )
            )
            await ses.commit()

        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/ideas")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    item = body[0]
    expected_keys = {
        "id", "tenant_id", "niche_id", "texto", "gancho",
        "entendible_nino_5_anos", "interesa_50_de_100",
        "universalidad", "intensidad", "claridad", "shareability",
        "distribucion", "alineacion", "rum_score", "rum_threshold_id",
        "passes_threshold", "approval_status", "origen_reintento_de", "created_at",
    }
    assert set(item.keys()) == expected_keys
    assert item["texto"] == "Escalar SaaS con contenido B2B"
    assert item["approval_status"] == "pending"


@pytest.mark.anyio
async def test_scripts_rows_expose_ddl_001_shape(db_session):
    """REQ-API-2 (API-02-2): una fila real → 200 con los keys del DDL scripts."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        from backend.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as ses:
            ses.add(Tenant(id=TENANT_B, name="Scripts Tenant"))
            await ses.commit()
            ses.add(
                Script(
                    id=SCRIPT_TEST_ID,
                    tenant_id=TENANT_B,
                    idea_id=IDEA_TEST_ID,
                    gancho_0_5s="Gancho llamativo",
                    contexto_5_30s="Contexto desarrollado",
                    moraleja_30_50s="Moraleja del video",
                    cta_50_60s="Agenda una llamada",
                    keyword="CONSULTA",
                )
            )
            await ses.commit()

        response = await ac.get(f"/api/v1/tenants/{TENANT_B}/scripts")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    expected_keys = {
        "id", "tenant_id", "idea_id", "gancho_0_5s", "contexto_5_30s",
        "moraleja_30_50s", "cta_50_60s", "keyword", "created_at",
    }
    assert set(body[0].keys()) == expected_keys
    assert body[0]["keyword"] == "CONSULTA"


@pytest.mark.anyio
async def test_brain_persona_ok_when_niche_row_exists(db_session):
    """D5: con una fila de niches con personaje_marca_json → status ok + persona parseado."""
    from backend.db.session import AsyncSessionLocal
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with AsyncSessionLocal() as ses:
            ses.add(Tenant(id=TENANT_BRAIN, name="Brain Tenant"))
            await ses.commit()
            ses.add(
                Niche(
                    id=NICHE_TEST_ID,
                    tenant_id=TENANT_BRAIN,
                    micronicho="Marketing B2B para CPAs",
                    ppp="Conseguir 50 socios en 30 días",
                    personaje_marca_json={
                        "atributos": ["Claro", "Directo"],
                        "estilo": "consultivo",
                    },
                )
            )
            await ses.commit()

        response = await ac.get(f"/api/v1/tenants/{TENANT_BRAIN}/brain")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["persona"] == {"atributos": ["Claro", "Directo"], "estilo": "consultivo"}
    assert body["chunks"] == []
    assert "1240" not in response.text


@pytest.mark.anyio
async def test_scripts_db_error_returns_503(db_session):
    """REQ-API-2 (API-02-2): si la capa de DB falla → 503 explícito, nunca datos falsos."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await db_session.execute(text("DROP TABLE scripts"))
        await db_session.commit()
        response = await ac.get(f"/api/v1/tenants/{TENANT_A}/scripts")
    assert response.status_code == 503