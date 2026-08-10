"""
test_daos.py

DAO layer tests for WU-02a (design D3/D4/D8, REQ-PERSIST-01/02/03/05):

- `test_product_columns_match_migration_004_exact` — PERSIST-01-2 ORM/DDL column
  parity on the `Product` model (same drift-proof pattern as
  `test_video_metric_orm_alignment.py`).
- `test_daos_insert_ideas_returns_rows` — PERSIST-02-1 unit: one `ideas` row per
  candidate, with a real generated UUID usable as FK downstream.
- `test_daos_insert_script_fks_selected_idea` — PERSIST-02-1 unit: `scripts` row
  FK to the approved idea.
- `test_daos_insert_video_fks_script` — PERSIST-02-1 unit: `videos` row FK to the
  script with raw/edited URIs captured.
- `test_daos_upsert_product` — REQ-PERSIST-05: `products` upsert by
  (tenant_id, name) persists `product_image_url`.
- `test_daos_update_idea_approval_changes_status` — PERSIST-03 unit: approval
  status is a real DB commit.
- `test_daos_update_idea_approval_non_uuid_returns_false` — T-08 acceptance:
  non-UUID idea ids (e2e `"idea-e2e-001"`) are a no-op `False`, never an error.

All tests run on the shared SQLite `db_session` fixture (StaticPool): DAOs open
their own `AsyncSessionLocal` (per-node unit-of-work) and rows are read back
through the fixture session, proving the shared in-memory DB contract.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from backend.db.models import Idea, Product, Script, Tenant, Video
from backend.db.daos import (
    insert_ideas,
    insert_script,
    insert_video,
    update_idea_approval,
    update_video_publish,
    upsert_product,
)

# Prefijo de filas propio de este archivo (cccc…) — el motor SQLite en memoria
# se comparte para TODA la sesión de pytest (StaticPool, conftest.py); otros
# archivos usan 1111/aaaa/bbbb… así que este archivo usa el suyo para no
# colisionar en UNIQUE constraints.
DAO_TENANT_ID = "cccc0001-1111-2222-3333-444444444444"
DAO_TENANT_2_ID = "cccc0002-1111-2222-3333-444444444444"

PRODUCT_004_COLUMNS = {
    "id",
    "tenant_id",
    "name",
    "description",
    "product_image_url",
    "created_at",
}

IDEA_PAYLOAD = {
    "texto": "3 Errores Críticos al Escalar SaaS en 2026",
    "gancho": "Si trabajas en SaaS, deja de cometer este error hoy mismo",
    "entendible_nino_5_anos": True,
    "interesa_50_de_100": True,
    "universalidad": 0.85,
    "intensidad": 0.9,
    "claridad": 0.95,
    "shareability": 0.8,
    "distribucion": 0.85,
    "alineacion": 0.9,
    "rum_score": 0.87,
    "passes_5_50": True,
}

SCRIPT_PAYLOAD = {
    "gancho_0_5s": "Tu equipo vende sin contenido",
    "contexto_5_30s": "El problema no es la falta de herramientas",
    "moraleja_30_50s": "Primero domina la tracción orgánica",
    "cta_50_60s": "Comenta CONSULTA abajo",
    "keyword": "CONSULTA",
}


@pytest.fixture
async def dao_tenants(db_session):
    """Garantiza los tenants de este archivo una sola vez.

    El SQLite en memoria se comparte para TODA la sesión de pytest (StaticPool,
    conftest.py), así que re-seedear el mismo tenants.id en cada test rompería
    UNIQUE. Este fixture es idempotente: sólo inserta los tenants faltantes.
    """
    existing = set(
        (
            await db_session.execute(
                select(Tenant.id).where(
                    Tenant.id.in_([DAO_TENANT_ID, DAO_TENANT_2_ID])
                )
            )
        ).scalars().all()
    )
    for tid, name in ((DAO_TENANT_ID, "DAO Tenant A"), (DAO_TENANT_2_ID, "DAO Tenant B")):
        if tid not in existing:
            db_session.add(Tenant(id=tid, name=name))
    await db_session.commit()


def test_product_columns_match_migration_004_exact():
    """PERSIST-01-2: `Product` MUST mirror migration 004 columns exactly (DDL-as-truth)."""
    cols = {c.name for c in Product.__table__.columns}
    assert cols == PRODUCT_004_COLUMNS, (
        f"Product drift: got {sorted(cols)} expected {sorted(PRODUCT_004_COLUMNS)}"
    )


@pytest.mark.anyio
async def test_daos_insert_ideas_returns_rows(db_session, dao_tenants):
    """PERSIST-02-1 unit: one `ideas` row per candidate with a real, reusable UUID."""
    rows = await insert_ideas(
        DAO_TENANT_ID,
        [IDEA_PAYLOAD, {**IDEA_PAYLOAD, "texto": "La Verdad Incómoda sobre el SaaS"}],
    )

    assert len(rows) == 2
    assert rows[0].texto == IDEA_PAYLOAD["texto"]
    assert rows[0].approval_status == "pending"
    assert rows[0].tenant_id == DAO_TENANT_ID
    # El id es un UUID real generado por el DAO (reutilizable como FK downstream)
    assert str(rows[0].id)

    persisted = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == DAO_TENANT_ID))
    ).scalars().all()
    assert len(persisted) == 2
    assert {i.texto for i in persisted} == {
        IDEA_PAYLOAD["texto"],
        "La Verdad Incómoda sobre el SaaS",
    }
    # La clave interna del crew (passes_5_50) se mapea a la columna DDL passes_threshold
    assert persisted[0].passes_threshold is True


@pytest.mark.anyio
async def test_daos_insert_script_fks_selected_idea(db_session, dao_tenants):
    """PERSIST-02-1 unit: `scripts` row FK to the idea row returned by insert_ideas."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(DAO_TENANT_ID, idea_row.id, SCRIPT_PAYLOAD)

    assert script_row.idea_id == idea_row.id
    assert script_row.tenant_id == DAO_TENANT_ID
    assert script_row.keyword == "CONSULTA"
    assert script_row.gancho_0_5s == SCRIPT_PAYLOAD["gancho_0_5s"]

    persisted = (
        await db_session.execute(select(Script).where(Script.tenant_id == DAO_TENANT_ID))
    ).scalars().all()
    assert len(persisted) == 1
    assert persisted[0].idea_id == idea_row.id  # FK real hacia la idea persistida


@pytest.mark.anyio
async def test_daos_insert_video_fks_script(db_session, dao_tenants):
    """PERSIST-02-1 unit: `videos` row FK to the script with raw/edited URIs captured."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(DAO_TENANT_ID, idea_row.id, SCRIPT_PAYLOAD)
    video_row = await insert_video(
        DAO_TENANT_ID,
        script_row.id,
        raw_video_uri=f"s3://viralsync-media-dev/{DAO_TENANT_ID}/raw_input.mp4",
        edited_video_uri=f"http://static.viralsync/{DAO_TENANT_ID}/final.mp4",
    )

    assert video_row.script_id == script_row.id
    assert video_row.tenant_id == DAO_TENANT_ID
    assert video_row.raw_video_uri.endswith("raw_input.mp4")
    assert video_row.edited_video_uri.endswith("final.mp4")
    assert video_row.publish_approval_status == "pending"

    persisted = (
        await db_session.execute(select(Video).where(Video.tenant_id == DAO_TENANT_ID))
    ).scalars().all()
    assert len(persisted) == 1
    assert persisted[0].script_id == script_row.id
    assert persisted[0].edited_video_uri == video_row.edited_video_uri


@pytest.mark.anyio
async def test_daos_upsert_product(db_session, dao_tenants):
    """REQ-PERSIST-05: re-ingest del mismo name actualiza; name distinto agrega fila."""
    first = await upsert_product(
        DAO_TENANT_ID,
        {
            "name": "Suplemento Alpha Mind",
            "description": "Nootrópico natural",
            "product_image_url": "http://minio:9000/viralsync-media/alpha.png",
        },
    )
    assert first.product_image_url.endswith("alpha.png")

    updated = await upsert_product(
        DAO_TENANT_ID,
        {
            "name": "Suplemento Alpha Mind",
            "description": "Nootrópico natural v2",
            "product_image_url": "http://minio:9000/viralsync-media/alpha-v2.png",
        },
    )
    assert updated.description == "Nootrópico natural v2"

    rows = (
        await db_session.execute(select(Product).where(Product.tenant_id == DAO_TENANT_ID))
    ).scalars().all()
    assert len(rows) == 1, "upsert del mismo name no debe duplicar filas"
    assert rows[0].description == "Nootrópico natural v2"
    assert rows[0].product_image_url.endswith("alpha-v2.png")

    # Triangulación: otro producto del mismo tenant → segunda fila
    await upsert_product(
        DAO_TENANT_ID,
        {
            "name": "Plan Consultoría SaaS",
            "description": "Servicio intangible",
            "product_image_url": "http://minio:9000/viralsync-media/consult.png",
        },
    )
    rows = (
        await db_session.execute(select(Product).where(Product.tenant_id == DAO_TENANT_ID))
    ).scalars().all()
    assert len(rows) == 2
    assert {p.name for p in rows} == {"Suplemento Alpha Mind", "Plan Consultoría SaaS"}


@pytest.mark.anyio
async def test_daos_update_idea_approval_changes_status(db_session, dao_tenants):
    """PERSIST-03 unit: approval_status es un commit real en la fila ideas."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]
    assert idea_row.approval_status == "pending"

    ok = await update_idea_approval(DAO_TENANT_ID, idea_row.id, "approved")
    assert ok is True

    rows = (
        await db_session.execute(
            select(Idea)
            .where(Idea.id == idea_row.id)
            .execution_options(populate_existing=True)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].approval_status == "approved"

    # PERSIST-03-2: rejection también commitea en la misma fila
    ok_rejected = await update_idea_approval(DAO_TENANT_ID, idea_row.id, "rejected")
    assert ok_rejected is True
    rows = (
        await db_session.execute(
            select(Idea)
            .where(Idea.id == idea_row.id)
            .execution_options(populate_existing=True)
        )
    ).scalars().all()
    assert rows[0].approval_status == "rejected"


@pytest.mark.anyio
async def test_daos_update_idea_approval_non_uuid_returns_false(db_session, dao_tenants):
    """T-08 acceptance: idea no-UUID (e2e "idea-e2e-001") → no-op False, sin error."""
    ok = await update_idea_approval(DAO_TENANT_ID, "idea-e2e-001", "approved")
    assert ok is False


@pytest.mark.anyio
async def test_daos_update_idea_approval_other_tenant_returns_false(db_session, dao_tenants):
    """update_idea_approval está scoped por tenant: id válido de otro tenant → False."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]

    ok = await update_idea_approval(DAO_TENANT_2_ID, idea_row.id, "approved")
    assert ok is False  # la fila pertenece a DAO_TENANT_ID, no a B

    rows = (
        await db_session.execute(select(Idea).where(Idea.id == idea_row.id))
    ).scalars().all()
    assert rows[0].approval_status == "pending"  # sin efecto colateral


@pytest.mark.anyio
async def test_daos_update_video_publish_changes_row(db_session, dao_tenants):
    """REQ-PTT-01 (D-F) unit: `update_video_publish` es UN UPDATE real — setea
    `instagram_post_id` + `published_at` y NO toca `publish_approval_status`
    (CHECK-safe: la DDL 001 nunca ve 'published')."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(DAO_TENANT_ID, idea_row.id, SCRIPT_PAYLOAD)
    video_row = await insert_video(
        DAO_TENANT_ID,
        script_row.id,
        raw_video_uri=f"s3://viralsync-media-dev/{DAO_TENANT_ID}/raw_input.mp4",
        edited_video_uri=f"http://static.viralsync/{DAO_TENANT_ID}/final.mp4",
    )

    published_at = datetime.now(timezone.utc)
    ok = await update_video_publish(
        DAO_TENANT_ID, video_row.id, "ig_reel_dao_write_back", published_at
    )
    assert ok is True

    rows = (
        await db_session.execute(
            select(Video)
            .where(Video.id == video_row.id)
            .execution_options(populate_existing=True)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].instagram_post_id == "ig_reel_dao_write_back"
    assert rows[0].published_at is not None
    assert rows[0].publish_approval_status == "pending"  # el write-back no la toca


@pytest.mark.anyio
async def test_daos_update_video_publish_non_uuid_returns_false(db_session, dao_tenants):
    """REQ-PTT-01: video_id no-UUID → no-op False, sin error (mismo patrón _is_uuid)."""
    ok = await update_video_publish(
        DAO_TENANT_ID, "not-a-video-id", "ig_reel_x", datetime.now(timezone.utc)
    )
    assert ok is False


@pytest.mark.anyio
async def test_daos_update_video_publish_other_tenant_returns_false(db_session, dao_tenants):
    """REQ-PTT-01: `update_video_publish` está scoped por tenant — id de otro tenant → False."""
    idea_row = (await insert_ideas(DAO_TENANT_ID, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(DAO_TENANT_ID, idea_row.id, SCRIPT_PAYLOAD)
    video_row = await insert_video(
        DAO_TENANT_ID,
        script_row.id,
        raw_video_uri=f"s3://viralsync-media-dev/{DAO_TENANT_ID}/raw_input.mp4",
        edited_video_uri=f"http://static.viralsync/{DAO_TENANT_ID}/final.mp4",
    )

    ok = await update_video_publish(
        DAO_TENANT_2_ID, video_row.id, "ig_reel_x", datetime.now(timezone.utc)
    )
    assert ok is False  # la fila pertenece a DAO_TENANT_ID, no a B