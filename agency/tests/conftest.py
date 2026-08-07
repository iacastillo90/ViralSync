"""
conftest.py

Fixtures globales para pytest.
Forzar Celery Eager Mode y variables de desarrollo sin modificar DBs locales.
"""

import os

# Fuerza SQLite en-memoria compartido (StaticPool) para toda la sesión de pytest.
# Debe fijarse ANTES de importar backend.db.session para que el engine eager
# no apunte a PostgreSQL/5432 (inaccesible en CI/local).
os.environ["FORCE_SQLITE"] = "true"

import pytest  # noqa: E402

from backend.db.session import init_db, AsyncSessionLocal  # noqa: E402


@pytest.fixture(autouse=True)
def set_testing_env(monkeypatch):
    """Fuerza variables de entorno para testing síncrono en dev."""
    monkeypatch.setenv("AGENCY_ENV", "dev")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "True")
    monkeypatch.setenv("CELERY_TASK_EAGER_PROPAGATES", "True")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "secreto_meta_test_secret")


@pytest.fixture
async def init_test_db():
    """Crea el esquema en SQLite en memoria (idempotente por create_all).

    Es una fixture async NO-autouse: sync tests (prune/rum/filters, etc.)
    no tocan la BD y no deben disparar un cualquier-anyio. Las tests que
    consultan DB (fastapi endpoints, e2e pipeline, phases) la piden
    explícitamente como argumento.
    """
    await init_db()
    yield


@pytest.fixture
async def db_session(init_test_db):
    """Sesión asíncrona sobre el motor SQLite en memoria compartido."""
    async with AsyncSessionLocal() as session:
        yield session