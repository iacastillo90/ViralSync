"""
test_competitor_benchmark_api.py

Pruebas TDD del Competitor Benchmark (S4 — PR #4):
- T-S4-05: router `competitors` — GET/POST/PATCH (toggle is_active) y trigger de
  ingestión manual (REQ-COMP-01, REQ-COMP-02).
- T-S4-06: `GET /{tenant}/rag/benchmark` — propios vs competidores, top-N por
  similitud + gap analysis determinista por estructura, y exclusión de cuentas
  inactivas (REQ-COMP-04).

Se usa la DB SQLite en memoria (create_all vía init_test_db) y mocks de
`get_winning_patterns`/`ingest_competitor` para no depender de Qdrant/SearXNG.
"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.main import app
from backend.security.auth import create_access_token
from backend.db.session import AsyncSessionLocal
from backend.db.models import Tenant, CompetitorAccount


def _auth_header(tenant_id: str) -> dict:
    token = create_access_token(
        user_id=f"user-comp-{tenant_id[:8]}", tenant_id=tenant_id, role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded_tenant(init_test_db):
    """Tenant aislado por UUID único por test (SQLite :memory: compartido)."""
    tenant_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        session.add(Tenant(id=tenant_id, name="Competitor Tenant"))
        await session.commit()
    return tenant_id


async def _create_account(tenant_id: str, **overrides) -> str:
    """Crea una CompetitorAccount vía ORM y devuelve su id."""
    fields = dict(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        username="viral_competitor",
        niche="Fitness",
        is_active=True,
    )
    fields.update(overrides)
    async with AsyncSessionLocal() as session:
        session.add(CompetitorAccount(**fields))
        await session.commit()
    return fields["id"]


# ---------------------------------------------------------------------------
# T-S4-05 — Router competitors (CRUD + trigger ingestión manual)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_competitor_persists(seeded_tenant):
    """REQ-COMP-01: POST /competitors crea la cuenta con tenant/platform/niche."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{seeded_tenant}/competitors",
            headers=_auth_header(seeded_tenant),
            json={
                "platform": "instagram",
                "username": "competidor_viral",
                "display_name": "Competidor Viral",
                "niche": "Fitness",
            },
        )
    assert response.status_code == 201, f"Recibió {response.status_code}: {response.text}"
    data = response.json()
    assert data["username"] == "competidor_viral"
    assert data["niche"] == "Fitness"
    assert data["is_active"] is True

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(CompetitorAccount).where(CompetitorAccount.username == "competidor_viral")
            )
        ).scalars().one()
        assert row.tenant_id == seeded_tenant
        assert row.platform == "instagram"
        assert row.niche == "Fitness"


@pytest.mark.anyio
async def test_list_competitors_scoped_by_tenant(seeded_tenant):
    """REQ-COMP-01: GET /competitors lista las cuentas del tenant (activas e inactivas)."""
    other_tenant = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        session.add(Tenant(id=other_tenant, name="Other Tenant"))
        await session.commit()
    # La persistencia se verifica vía GET más abajo; el id retornado no se usa.
    await _create_account(seeded_tenant, username="mine")
    await _create_account(seeded_tenant, username="inactive", is_active=False)
    await _create_account(other_tenant, username="other_tenant_account")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{seeded_tenant}/competitors",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 200
    usernames = {c["username"] for c in response.json()}
    assert usernames == {"mine", "inactive"}, "Solo las cuentas del tenant deben listarse"
    assert "other_tenant_account" not in usernames


@pytest.mark.anyio
async def test_patch_toggles_is_active(seeded_tenant):
    """REQ-COMP-04: PATCH /competitors/{id} alterna is_active (true -> false -> true)."""
    account_id = await _create_account(seeded_tenant, is_active=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first = await ac.patch(
            f"/api/v1/tenants/{seeded_tenant}/competitors/{account_id}",
            headers=_auth_header(seeded_tenant),
        )
        second = await ac.patch(
            f"/api/v1/tenants/{seeded_tenant}/competitors/{account_id}",
            headers=_auth_header(seeded_tenant),
        )
    assert first.status_code == 200, f"Recibió {first.status_code}: {first.text}"
    assert first.json()["is_active"] is False
    assert second.status_code == 200
    assert second.json()["is_active"] is True

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(CompetitorAccount).where(CompetitorAccount.id == account_id))
        ).scalars().one()
        assert row.is_active is True


@pytest.mark.anyio
async def test_patch_unknown_competitor_404(seeded_tenant):
    """PATCH sobre una cuenta inexistente devuelve 404 (no inventa datos)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/v1/tenants/{seeded_tenant}/competitors/{uuid.uuid4()}",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ingest_endpoint_triggers_service(seeded_tenant, monkeypatch):
    """REQ-COMP-02: POST /competitors/{id}/ingest dispara ingest_competitor (manual)."""
    account_id = await _create_account(seeded_tenant, username="fitness_viral")

    import backend.services.competitor_ingest as competitor_ingest_module

    async def fake_ingest(account):
        return 3

    monkeypatch.setattr(competitor_ingest_module, "ingest_competitor", fake_ingest)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{seeded_tenant}/competitors/{account_id}/ingest",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 200, f"Recibió {response.status_code}: {response.text}"
    data = response.json()
    assert data["account_id"] == account_id
    assert data["indexed_hooks"] == 3


# ---------------------------------------------------------------------------
# T-S4-06 — GET /{tenant}/rag/benchmark
# ---------------------------------------------------------------------------


def _patch_winning_patterns(monkeypatch, own, competitor):
    def fake_get(niche="", query="", limit=3, source=None):
        if source == "competitor":
            return list(competitor)[: max(limit * 4, limit)]
        return list(own)[: max(limit * 4, limit)]

    monkeypatch.setattr(
        "backend.services.rag_context.get_winning_patterns", fake_get
    )


@pytest.mark.anyio
async def test_benchmark_excludes_inactive_account(seeded_tenant, monkeypatch):
    """REQ-COMP-04 (escenario 2): el hook de una cuenta inactiva no entra al benchmark
    ni al gap analysis — solo estructuras de competidores con cuenta activa."""
    active_id = await _create_account(seeded_tenant, username="active_competitor")
    inactive_id = await _create_account(seeded_tenant, username="inactive_competitor", is_active=False)

    own = [
        {"pattern_text": "¿Sabías que el 90% de las personas comete este error?", "source": "own"},
        {"pattern_text": "Este secreto cambió nuestra estrategia de contenido", "source": "own"},
    ]
    # El hook de la cuenta inactiva tiene una estructura que NO está en las propias;
    # si entrara al benchmark, el gap aparecería y el test fallaría.
    competitor = [
        {"pattern_text": "5 errores que debes evitar al entrenar", "source": "competitor", "account_id": active_id},
        {"pattern_text": "Stop de hacer esto si quieres resultados", "source": "competitor", "account_id": inactive_id},
    ]
    _patch_winning_patterns(monkeypatch, own, competitor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{seeded_tenant}/rag/benchmark?niche=Fitness&limit=5",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 200, f"Recibió {response.status_code}: {response.text}"
    data = response.json()
    assert set(data) == {"own_hooks", "competitor_hooks", "top_similar", "gaps"}

    competitor_texts = [h["pattern_text"] for h in data["competitor_hooks"]]
    assert "5 errores que debes evitar al entrenar" in competitor_texts
    assert "Stop de hacer esto si quieres resultados" not in competitor_texts, (
        "El hook de la cuenta inactiva debe excluirse (REQ-COMP-04 escenario 2)"
    )

    assert data["gaps"] == ["Lista Numérica + Valor Exclusivo"], (
        "El gap debe ser solo la estructura del competidor activo ausente en las propias; "
        "la estructura del inactivo (Comando de Interrupción) NO debe aparecer"
    )
    assert data["top_similar"]


@pytest.mark.anyio
async def test_benchmark_top_similar_sorted_by_similarity(seeded_tenant, monkeypatch):
    """REQ-COMP-04: top_similar devuelve los hooks competidores ordenados por
    similitud descendente al query del nicho."""
    active_id = await _create_account(seeded_tenant, username="active_competitor")

    own = [{"pattern_text": "Este secreto cambió nuestra estrategia de contenido", "source": "own"}]
    competitor = [
        {"pattern_text": "5 errores que debes evitar al entrenar", "source": "competitor", "account_id": active_id},
        {"pattern_text": "¿Por qué tu contenido no despega?", "source": "competitor", "account_id": active_id},
    ]
    _patch_winning_patterns(monkeypatch, own, competitor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{seeded_tenant}/rag/benchmark?niche=Fitness&limit=5",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 200
    data = response.json()
    scores = [item["score"] for item in data["top_similar"]]
    assert len(scores) == len(competitor)
    assert scores == sorted(scores, reverse=True), "top_similar debe ordenarse por similitud descendente"
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert len({item["pattern_text"] for item in data["top_similar"]}) == len(competitor)


@pytest.mark.anyio
async def test_benchmark_without_competitors_returns_empty_sections(seeded_tenant, monkeypatch):
    """REQ-COMP-04: sin cuentas competidoras activas el benchmark responde vacío (no falla)."""
    async with AsyncSessionLocal() as session:
        session.add(CompetitorAccount(id=str(uuid.uuid4()), tenant_id=seeded_tenant, username="x", is_active=False))
        await session.commit()

    own = [{"pattern_text": "¿Sabías que el 90% de las personas comete este error?", "source": "own"}]
    _patch_winning_patterns(monkeypatch, own, [])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/tenants/{seeded_tenant}/rag/benchmark?niche=Fitness&limit=5",
            headers=_auth_header(seeded_tenant),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["competitor_hooks"] == []
    assert data["top_similar"] == []
    assert data["gaps"] == []