"""
test_db_indexes.py

Pruebas unitarias de contrato (TDD) para la Fase 2: Indexación de DB y Consultas Async.
Verifica que la migración 006 exista y los modelos SQLAlchemy declaren los índices compuestos.
"""

from pathlib import Path
from backend.db.models import Idea, Lead, Video, VideoMetric


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
