"""
graph_execution_task.py

Tarea Celery duradera para la ejecución y reanudación de grafos LangGraph
fuera del proceso HTTP de Uvicorn (REQ-CGE-01/02).
"""

import asyncio
import logging
from typing import Dict, Any

from workers.celery_app import celery_app
from backend.routers.graph_execution import _run_graph_background, _resume_graph_background

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.graph_execution_task.run_graph_task", bind=True, max_retries=2)
def run_graph_task(self, tenant_id: str, initial_state: Dict[str, Any]) -> None:
    """Ejecuta el grafo multi-agente en un proceso worker Celery asíncrono."""
    logger.info(f"[{tenant_id}] Ejecutando run_graph_task en Celery Worker...")
    try:
        asyncio.run(_run_graph_background(tenant_id, initial_state))
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error en run_graph_task: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=5) from exc


@celery_app.task(name="workers.graph_execution_task.resume_graph_task", bind=True, max_retries=2)
def resume_graph_task(self, tenant_id: str, resume_payload: Dict[str, Any]) -> None:
    """Reanuda un grafo pausado desde una tarea Celery duradera."""
    logger.info(f"[{tenant_id}] Reanudando resume_graph_task en Celery Worker con payload {resume_payload}...")
    try:
        asyncio.run(_resume_graph_background(tenant_id, resume_payload))
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error en resume_graph_task: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=5) from exc
