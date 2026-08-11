"""
test_rum_learning_task.py

Pruebas unitarias para verificar la ejecución de rum_learning_task (REQ-RFL-01/02).
"""

import pytest
from unittest.mock import patch, MagicMock
from workers.celery_app import celery_app
from workers.rum_learning_task import run_rum_learning_task, fetch_top_performing_scripts


def test_celery_app_includes_rum_learning_task():
    """Verifica que workers.rum_learning_task esté registrado en celery_app."""
    assert "workers.rum_learning_task" in celery_app.conf.include
    assert "workers.rum_learning_task.*" in celery_app.conf.task_routes


def test_fetch_top_performing_scripts():
    """Verifica que fetch_top_performing_scripts retorne estructuras de guiones con tasa de retención."""
    scripts = fetch_top_performing_scripts("tenant_rum_test")
    assert isinstance(scripts, list)
    assert len(scripts) > 0
    assert "retention_rate_72h" in scripts[0]


@patch("qdrant_client.QdrantClient")
def test_run_rum_learning_task_indexes_examples(mock_qdrant_cls):
    """Verifica que run_rum_learning_task interactúe con Qdrant e inicie la colección."""
    mock_client = MagicMock()
    mock_collections = MagicMock()
    mock_collections.collections = []
    mock_client.get_collections.return_value = mock_collections
    mock_qdrant_cls.return_value = mock_client
    
    result = run_rum_learning_task("tenant_rum_test")
    
    assert result["status"] == "completed"
    assert result["indexed_examples"] > 0
