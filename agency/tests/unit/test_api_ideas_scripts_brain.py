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
from sqlalchemy import text, select

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

# IDs de filas en espacio propio de este archivo (prefijo aaaa…/eeee…) — el
# motor SQLite en memoria se comparte para TODA la sesión de pytest (StaticPool,
# conftest.py), así que cualquier UUID repetido entre archivos de test rompe
# UNIQUE constraints. test_video_metric_orm_alignment.py usa 1111/3333/…,
# test_enterprise_phases_0_to_5.py usa los suyos; este archivo usa el suyo.
IDEA_TEST_ID = "aaaa0001-5555-6666-7777-888888888888"
SCRIPT_TEST_ID = "aaaa0002-5555-6666-7777-888888888888"
NICHE_TEST_ID = "aaaa0003-5555-6666-7777-888888888888"

# Tenant + ideas dedicados a los tests de approve (PERSIST-03, WU-03): espacio
# propio (eeee…) para que el resume del grafo en background (que re-ejecuta
# node_ideation y escribe filas nuevas en el mismo DB compartido) nunca
# colisione con los conteos/asserts de otros tests.
APPROVE_TENANT_ID = "eeee0001-1111-2222-3333-444444444444"
APPROVED_IDEA_ID = "eeee0002-1111-2222-3333-444444444444"
REJECTED_IDEA_ID = "eeee0003-1111-2222-3333-444444444444"
INVALID_STATUS_IDEA_ID = "eeee0004-1111-2222-3333-444444444444"


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
        "approval_status", "trend_score", "trend_rationale", "rendered_videos",
        "voice_persona_id",
    }
    assert set(body[0].keys()) == expected_keys
    assert body[0]["keyword"] == "CONSULTA"
    # T-S2a-05: el campo voice_persona_id se expone siempre (None si no asignado).
    assert body[0]["voice_persona_id"] is None


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


# --------------------------------------------------------------------------- #
# Checkpoints humanos honestos — 202 + commit real (REQ-API-06 / PERSIST-03)
# --------------------------------------------------------------------------- #

@pytest.fixture
async def approve_tenant(db_session):
    """Garantiza el tenant dedicado de approve una sola vez (idempotente).

    Re-seedear el mismo tenants.id en cada test rompería UNIQUE; el fixture sólo
    inserta el tenant faltante (patrón `dao_tenants` de test_daos.py).
    """
    existing = (
        await db_session.execute(
            select(Tenant.id).where(Tenant.id == APPROVE_TENANT_ID)
        )
    ).scalars().first()
    if existing is None:
        db_session.add(Tenant(id=APPROVE_TENANT_ID, name="Approve Tenant"))
        await db_session.commit()


@pytest.mark.anyio
async def test_ideas_approve_commits_approval_status(db_session, approve_tenant):
    """PERSIST-03-1 / API-06-1: approve = UPDATE real de approval_status (202 + commit).

    REQ-API-06 (MODIFIED): el no-op histórico se revirtió — aprobar una idea
    pendiente con un UUID real DEBE persistir `approval_status="approved"` en la
    fila (verificado vía la sesión del fixture sobre el DB compartido) además de
    devolver el 202 {status:accepted, kind:idea_approval, queued:true, idea_id}.
    """
    db_session.add(
        Idea(
            id=APPROVED_IDEA_ID,
            tenant_id=APPROVE_TENANT_ID,
            texto="Idea pendiente para aprobar",
            approval_status="pending",
        )
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{APPROVE_TENANT_ID}/ideas/approve",
            json={"idea_id": APPROVED_IDEA_ID, "status": "approved"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["kind"] == "idea_approval"
    assert body["queued"] is True
    assert body["idea_id"] == APPROVED_IDEA_ID  # eco del id real, nunca fabricado

    row = (
        await db_session.execute(
            select(Idea)
            .where(Idea.id == APPROVED_IDEA_ID)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert row.approval_status == "approved", "approve DEBE commitear el status en la DB (no-op eliminado)"


@pytest.mark.anyio
async def test_ideas_reject_commits_rejected(db_session, approve_tenant):
    """PERSIST-03-2: reject también commitea — la fila queda `rejected`."""
    db_session.add(
        Idea(
            id=REJECTED_IDEA_ID,
            tenant_id=APPROVE_TENANT_ID,
            texto="Idea pendiente para rechazar",
            approval_status="pending",
        )
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{APPROVE_TENANT_ID}/ideas/approve",
            json={"idea_id": REJECTED_IDEA_ID, "status": "rejected"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["kind"] == "idea_approval"
    assert body["queued"] is True

    row = (
        await db_session.execute(
            select(Idea)
            .where(Idea.id == REJECTED_IDEA_ID)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert row.approval_status == "rejected"


@pytest.mark.anyio
async def test_publish_approve_returns_202_no_fabricated_post_id(db_session):
    """REQ-API-06 (D6): publish/approve → 202 sin published_post_id inventado (anti 'ig_reel_…_99812')."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{TENANT_A}/publish/approve",
            json={"status": "approved"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["kind"] == "publish_approval"
    assert body["queued"] is True
    assert "published_post_id" not in body
    assert "ig_reel_" not in response.text


# --------------------------------------------------------------------------- #
# Approve honesty — 0-row 404 + status allowlist (REQ-PTT-04 / D-E, TCK-007)
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_ideas_approve_unknown_id_returns_404_no_resume(monkeypatch, approve_tenant):
    """PTT-04-2 / D-E (TCK-007): approve con idea_id desconocido (UUID válido,
    0 filas) → 404 HONESTO (nunca 202), y el grafo NO se reanuda ni se emite
    evento SSE.

    El orden importa: el chequeo del DAO (bool) ocurre ANTES del broadcast +
    resume — un no-op no puede parecer progreso ante el frontend.
    """
    from backend.routers import graph_execution

    resume_calls = []
    fake_sse = _SseCapture()

    async def _counting_resume(tenant_id, resume_payload):
        resume_calls.append((tenant_id, resume_payload))

    monkeypatch.setattr(graph_execution, "_resume_graph_background", _counting_resume)
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)

    unknown_id = str(uuid.uuid4())  # formato UUID válido que no matchea ninguna fila
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{APPROVE_TENANT_ID}/ideas/approve",
            json={"idea_id": unknown_id, "status": "approved"},
        )
    assert response.status_code == 404, f"0-row approve debe ser 404, recibió {response.status_code}"
    assert response.json()["detail"] == "idea not found or stale"
    assert resume_calls == [], "un approve 0-row NO debe reanudar el grafo"
    assert fake_sse.broadcasts == [], "un approve 0-row NO debe emitir idea_checkpoint"


@pytest.mark.anyio
async def test_ideas_approve_invalid_status_returns_422(monkeypatch, db_session, approve_tenant):
    """PTT-04-3 / D-E (TCK-007): status fuera del allowlist {approved, rejected}
    → 422 validation (FastAPI), SIN commit y SIN resume del grafo."""
    from backend.routers import graph_execution

    db_session.add(
        Idea(
            id=INVALID_STATUS_IDEA_ID,
            tenant_id=APPROVE_TENANT_ID,
            texto="Idea pendiente para status inválido",
            approval_status="pending",
        )
    )
    await db_session.commit()

    resume_calls = []

    async def _counting_resume(tenant_id, resume_payload):
        resume_calls.append((tenant_id, resume_payload))

    monkeypatch.setattr(graph_execution, "_resume_graph_background", _counting_resume)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{APPROVE_TENANT_ID}/ideas/approve",
            json={"idea_id": INVALID_STATUS_IDEA_ID, "status": "published"},
        )
    assert response.status_code == 422, f"status inválido debe ser 422, recibió {response.status_code}"
    assert resume_calls == [], "un status inválido NO debe reanudar el grafo"

    row = (
        await db_session.execute(
            select(Idea)
            .where(Idea.id == INVALID_STATUS_IDEA_ID)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert row.approval_status == "pending", "un status inválido NO debe commitear nada"


@pytest.mark.anyio
async def test_publish_approve_invalid_status_returns_422(monkeypatch):
    """D-E (TCK-007): el modelo de publish/approve también allowlista status
    {approved, rejected} → 422, sin resume."""
    from backend.routers import graph_execution

    resume_calls = []

    async def _counting_resume(tenant_id, resume_payload):
        resume_calls.append((tenant_id, resume_payload))

    monkeypatch.setattr(graph_execution, "_resume_graph_background", _counting_resume)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{APPROVE_TENANT_ID}/publish/approve",
            json={"status": "published"},
        )
    assert response.status_code == 422, f"publish status inválido debe ser 422, recibió {response.status_code}"
    assert resume_calls == [], "un status inválido NO debe reanudar el grafo"


@pytest.mark.anyio
async def test_realtime_sse_dev_tenant_resolution():
    """Verifica que TenantContextMiddleware resuelva el tenant_id de /realtime/sse/{tenant_id} en dev."""
    from starlette.requests import Request
    from starlette.responses import Response
    from backend.security.auth import TenantContextMiddleware

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/realtime/sse/{TENANT_A}",
        "headers": [],
        "query_string": b"",
    }
    request = Request(scope)
    middleware = TenantContextMiddleware(app=None)

    captured_request = None
    async def dummy_call_next(req):
        nonlocal captured_request
        captured_request = req
        return Response("ok")

    await middleware.dispatch(request, dummy_call_next)
    assert captured_request.state.tenant_id == TENANT_A


@pytest.mark.anyio
async def test_realtime_sse_query_token_auth(monkeypatch):
    """Verifica que el parámetro ?token= resuelva el JWT en TenantContextMiddleware."""
    from starlette.requests import Request
    from starlette.responses import Response
    from backend.security.auth import TenantContextMiddleware

    token = create_access_token(user_id="usr_prod_001", tenant_id=TENANT_A, role="admin")
    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/realtime/sse/{TENANT_A}",
        "headers": [],
        "query_string": f"token={token}".encode("utf-8"),
    }
    request = Request(scope)
    middleware = TenantContextMiddleware(app=None)

    captured_request = None
    async def dummy_call_next(req):
        nonlocal captured_request
        captured_request = req
        return Response("ok")

    await middleware.dispatch(request, dummy_call_next)
    assert captured_request.state.tenant_id == TENANT_A


# --------------------------------------------------------------------------- #
# SSE honesty (REQ-PTT-03 / D-D, TCK-005): `graph_error` lleva `code` cuando el
# error tiene `.code` (NoCandidatesError) y `graph_complete` lleva `terminal`
# cuando final_state trae `terminal_state` — guardado por isinstance
# (final_state None de un fake no crashea).
# --------------------------------------------------------------------------- #


class _SseCapture:
    """Captura broadcasts + graph_errors del router (patrón de
    test_graph_execution_resilience._FakeSSE, + código opcional)."""

    def __init__(self):
        self.broadcasts = []
        self.errors = []  # (tenant_id, message, code)

    async def broadcast(self, tenant_id, event_type, data):
        self.broadcasts.append((tenant_id, event_type, data))

    async def emit_graph_error(self, tenant_id, message, code=None):
        self.errors.append((tenant_id, message, code))


class _FakeGraph:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    async def ainvoke(self, state, config=None):
        if self.error:
            raise self.error
        return self.result


@pytest.mark.anyio
async def test_graph_error_emits_code_for_coded_error(monkeypatch):
    """D-D/TCK-005: un error con `.code` (NoCandidatesError) en background →
    `graph_error` incluye `code="no_candidates"` (aditivo, nunca un mensaje
    genérico que borre la causa)."""
    from agents.errors import NoCandidatesError
    from backend.routers import graph_execution
    from backend.routers.graph_execution import _run_graph_background

    fake_sse = _SseCapture()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)
    monkeypatch.setattr(
        graph_execution,
        "build_agency_graph",
        lambda *a, **kw: _FakeGraph(error=NoCandidatesError("sin candidatas RUM")),
    )

    await _run_graph_background("tenant-slice2-code", {"tenant_id": "tenant-slice2-code"})

    assert len(fake_sse.errors) == 1
    assert fake_sse.errors[0][2] == "no_candidates"


@pytest.mark.anyio
async def test_graph_complete_emits_terminal_when_present(monkeypatch):
    """D-C/TCK-005: `graph_complete` lleva `terminal` cuando final_state trae
    `terminal_state`; y un final_state `None` (fake) NO crashea gracias al guard
    isinstance — sin broadcast y sin graph_error."""
    from backend.routers import graph_execution
    from backend.routers.graph_execution import _run_graph_background

    # Escenario 1: terminal presente → graph_complete con `terminal`
    fake_sse = _SseCapture()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)
    monkeypatch.setattr(
        graph_execution,
        "build_agency_graph",
        lambda *a, **kw: _FakeGraph(result={"tenant_id": "t", "ideas": ["i1"], "terminal_state": "term_rejected"}),
    )
    await _run_graph_background("tenant-slice2-term", {"tenant_id": "tenant-slice2-term"})

    events = [e for e in fake_sse.broadcasts if e[1] == "graph_complete"]
    assert len(events) == 1
    assert events[0][2]["terminal"] == "term_rejected"

    # Escenario 2: final_state None (fake) → guard isinstance, sin crash ni emisión
    fake_sse2 = _SseCapture()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse2)
    monkeypatch.setattr(graph_execution, "build_agency_graph", lambda *a, **kw: _FakeGraph(result=None))
    await _run_graph_background("tenant-slice2-none", {"tenant_id": "tenant-slice2-none"})

    assert fake_sse2.broadcasts == []
    assert fake_sse2.errors == []