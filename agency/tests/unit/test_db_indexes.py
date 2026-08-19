"""
test_db_indexes.py

Pruebas unitarias de contrato (TDD) para la Fase 2: Indexación de DB y Consultas Async.
Verifica que la migración 006 exista y los modelos SQLAlchemy declaren los índices compuestos.
"""

from pathlib import Path
from backend.db.models import Idea, Lead, Video, VideoMetric

_MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


def _read_migration(name: str) -> str:
    return (_MIGRATIONS_DIR / name).read_text()


def test_alembic_migration_006_exists():
    """Verifica que la migración 006 de índices de rendimiento exista en alembic/versions."""
    migration_path = Path(__file__).parents[2] / "alembic" / "versions" / "006_add_performance_indexes.py"
    assert migration_path.exists(), "La migración 006_add_performance_indexes.py debe existir"


def test_models_declare_compound_indexes():
    """Verifica que los modelos SQLAlchemy declaren los índices compuestos en __table_args__ o en la metadata."""
    models_to_check = [Idea, Lead, Video, VideoMetric]
    for model in models_to_check:
        indexes = getattr(model, "__table_args__", ())
        assert len(indexes) > 0, f"El modelo {model.__name__} debe declarar índices compuestos en __table_args__"


def test_migration_011_exists():
    """REQ-DM-LEAD-02: la migración 011 de calificación de leads existe."""
    migration_path = _MIGRATIONS_DIR / "011_leads_qualification.sql"
    assert migration_path.exists(), "La migración 011_leads_qualification.sql debe existir"


def test_migration_011_declares_qualification_schema():
    """REQ-DM-LEAD-02: la migración declara qualification_score, platform, dedup_hash,
    DROP NOT NULL de video_id (el webhook no trae video) y los índices uq/idx."""
    sql = _read_migration("011_leads_qualification.sql")

    assert "qualification_score" in sql and "INTEGER" in sql
    assert "platform" in sql and "instagram" in sql
    assert "dedup_hash" in sql
    assert "DROP NOT NULL" in sql, "video_id debe pasar a nullable (webhook sin video)"
    assert "uq_leads_dedup_hash" in sql
    assert "idx_leads_status" in sql


def test_lead_model_declares_qualification_columns():
    """REQ-DM-LEAD-02 + REQ-DM-LEAD-01/05: el modelo Lead declara qualification_score,
    platform, dedup_hash y el índice idx_leads_status alineados con la migración 011."""
    lead_table = Lead.__table__
    assert "qualification_score" in lead_table.c
    assert lead_table.c.qualification_score.type.python_type is int
    assert "platform" in lead_table.c
    assert lead_table.c.platform.default.arg == "instagram"
    assert "dedup_hash" in lead_table.c
    assert lead_table.c.dedup_hash.unique is True, "dedup_hash debe ser UNIQUE (REQ-DM-LEAD-05)"
    assert lead_table.c.video_id.nullable is True, "video_id debe ser nullable (webhook sin video)"
    assert any(idx.name == "idx_leads_status" for idx in lead_table.indexes)
