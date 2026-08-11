"""
test_celery_graph_execution.py

Pruebas unitarias para verificar la orquestación del grafo LangGraph vía Celery (REQ-CGE-01/02/03).
"""

from unittest.mock import patch, MagicMock
import pytest
from workers.celery_app import celery_app
from workers.graph_execution_task import run_graph_task, resume_graph_task


def test_celery_app_includes_graph_execution_task():
    """Verifica que workers.graph_execution_task esté registrado en celery_app."""
    assert "workers.graph_execution_task" in celery_app.conf.include
    assert "workers.graph_execution_task.*" in celery_app.conf.task_routes


@patch("workers.graph_execution_task._run_graph_background")
def test_run_graph_task_executes_coroutine(mock_run):
    """Verifica que run_graph_task invoque _run_graph_background."""
    tenant_id = "tenant_test_celery"
    initial_state = {"tenant_id": tenant_id, "niche": "b2b"}
    
    run_graph_task(tenant_id, initial_state)
    
    mock_run.assert_called_once_with(tenant_id, initial_state)


@patch("workers.graph_execution_task._resume_graph_background")
def test_resume_graph_task_executes_coroutine(mock_resume):
    """Verifica que resume_graph_task invoque _resume_graph_background."""
    tenant_id = "tenant_test_celery"
    payload = {"idea_approved": True, "idea_rejected": False}
    
    resume_graph_task(tenant_id, payload)
    
    mock_resume.assert_called_once_with(tenant_id, payload)
