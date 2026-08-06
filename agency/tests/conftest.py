"""
conftest.py

Fixtures globales para pytest.
Forzar Celery Eager Mode y variables de desarrollo sin modificar DBs locales.
"""

import pytest


@pytest.fixture(autouse=True)
def set_testing_env(monkeypatch):
    """Fuerza variables de entorno para testing síncrono en dev."""
    monkeypatch.setenv("AGENCY_ENV", "dev")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "True")
    monkeypatch.setenv("CELERY_TASK_EAGER_PROPAGATES", "True")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "secreto_meta_test_secret")
