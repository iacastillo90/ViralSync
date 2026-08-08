"""
test_video_metric_orm_alignment.py

Drift-proof tests locking the ORM models to the migration DDLs:

- REQ-VID-1 (VID-01-01): VideoMetric column set == migration 002 exactly
  (`002_add_video_metrics_and_fix_leads.sql`) and none of the phantom
  columns that caused the /metrics 503.
- REQ-VID-1 (VID-01-02): insert/select regression via init_test_db
  (create_all) — a real SELECT over the aligned model must not raise
  UndefinedColumn / "no such column".
- Idea and Niche column sets locked to migration `001_init_schema.sql`
  (design D3 + D5): same drift mechanism that 503'd /metrics would
  otherwise reintroduce on /ideas and /brain.
"""

import uuid

import pytest
from sqlalchemy import select

from backend.db.models import VideoMetric, Idea, Niche, Tenant

VIDEO_METRIC_002_COLUMNS = {
    "id",
    "tenant_id",
    "video_id",
    "views_72h",
    "likes",
    "comments",
    "shares",
    "ratio_relativo",
    "classification",
    "action_taken",
    "captured_at",
}

VIDEO_METRIC_PHANTOM_COLUMNS = {
    "published_at",
    "views",
    "followers_at_posting",
    "leads_generated",
    "completion_rate",
    "engagement_rate",
    "created_at",
}

IDEA_001_COLUMNS = {
    "id",
    "tenant_id",
    "niche_id",
    "texto",
    "gancho",
    "entendible_nino_5_anos",
    "interesa_50_de_100",
    "universalidad",
    "intensidad",
    "claridad",
    "shareability",
    "distribucion",
    "alineacion",
    "rum_score",
    "rum_threshold_id",
    "passes_threshold",
    "approval_status",
    "origen_reintento_de",
    "created_at",
}

IDEA_PHANTOM_COLUMNS = {"niche", "score_rum", "status"}

NICHE_001_COLUMNS = {
    "id",
    "tenant_id",
    "micronicho",
    "ppp",
    "personaje_marca_json",
    "created_at",
}


def test_video_metric_columns_match_migration_002_exactly():
    """REQ-VID-1 VID-01-01: column-set read-back assertion."""
    cols = {c.name for c in VideoMetric.__table__.columns}
    assert cols == VIDEO_METRIC_002_COLUMNS, (
        f"VideoMetric drift: got {sorted(cols)} expected {sorted(VIDEO_METRIC_002_COLUMNS)}"
    )
    phantom = cols & VIDEO_METRIC_PHANTOM_COLUMNS
    assert not phantom, f"VideoMetric must not declare {sorted(phantom)} (absent from migration 002)"


def test_idea_columns_match_ddl_001_exact():
    """Idea must mirror DDL 001 (design D3) — the same 503 mechanism on /ideas."""
    cols = {c.name for c in Idea.__table__.columns}
    assert cols == IDEA_001_COLUMNS, (
        f"Idea drift: got {sorted(cols)} expected {sorted(IDEA_001_COLUMNS)}"
    )
    phantom = cols & IDEA_PHANTOM_COLUMNS
    assert not phantom, f"Idea must not declare phantom columns {sorted(phantom)}"


def test_niche_columns_match_ddl_001_exact():
    """Niche (design D5 brain persona source) must mirror DDL 001 niches."""
    cols = {c.name for c in Niche.__table__.columns}
    assert cols == NICHE_001_COLUMNS, (
        f"Niche drift: got {sorted(cols)} expected {sorted(NICHE_001_COLUMNS)}"
    )


@pytest.mark.anyio
async def test_video_metric_insert_then_select_no_undefined_column(db_session):
    """VID-01-02: insert via ORM with aligned columns; select must not raise."""
    tenant_id = "11111111-2222-3333-4444-555555555555"
    db_session.add(Tenant(id=tenant_id, name="Drift Tenant"))
    await db_session.commit()

    metric = VideoMetric(
        id="99999999-8888-7777-6666-555555555555",
        tenant_id=tenant_id,
        video_id="12345678-1234-1234-1234-123456789012",
        views_72h=120,
        likes=45,
        comments=7,
        shares=3,
        ratio_relativo=2.0,
        classification="VERDE",
        action_taken="Generar 3 variaciones",
    )
    db_session.add(metric)
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(VideoMetric).where(VideoMetric.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].views_72h == 120
    assert float(rows[0].ratio_relativo) == 2.0
    assert rows[0].classification == "VERDE"
    assert rows[0].action_taken == "Generar 3 variaciones"


@pytest.mark.anyio
async def test_idea_insert_select_uses_ddl_001_columns(db_session):
    """design D3: select(Idea) works with DDL 001 column names."""
    tenant_id = "33333333-4444-5555-6666-777777777777"
    db_session.add(Tenant(id=tenant_id, name="Idea Tenant"))
    await db_session.commit()

    idea = Idea(
        id="44444444-5555-6666-7777-888888888888",
        tenant_id=tenant_id,
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
    db_session.add(idea)
    await db_session.commit()

    rows = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].texto == "Escalar SaaS con contenido B2B"
    assert rows[0].approval_status == "pending"
    assert rows[0].rum_score is not None


@pytest.mark.anyio
async def test_niche_select_and_json_read_back(db_session):
    """design D5: persona JSON parsed back from the ORM Niche row."""
    tenant_id = "55555555-6666-7777-8888-999999999999"
    db_session.add(Tenant(id=tenant_id, name="Niche Tenant"))
    await db_session.commit()

    persona = {"atributos": ["Claro", "Directo"], "estilo": "consultivo"}
    db_session.add(
        Niche(
            id="66666666-7777-8888-9999-000000000000",
            tenant_id=tenant_id,
            micronicho="Marketing B2B para CPAs",
            ppp="Conseguir 50 socios en 30 días",
            personaje_marca_json=persona,
        )
    )
    await db_session.commit()

    rows = (
        await db_session.execute(select(Niche).where(Niche.tenant_id == tenant_id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].micronicho == "Marketing B2B para CPAs"
    assert rows[0].personaje_marca_json == persona