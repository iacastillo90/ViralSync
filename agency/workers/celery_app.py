"""
celery_app.py

Instancia principal de Celery para tareas asíncronas en segundo plano.
Configuración de concurrencia serializada (concurrency=1 en dev) y modo Eager en testing.
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "viralsync_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.video_edit_task",
        "workers.metrics_loop_task",
        "workers.webhook_dlq_task",
        "workers.trend_scraper_task",
        "workers.graph_execution_task",
        "workers.rum_learning_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "workers.video_edit_task.*": {"queue": "rendering"},
        "workers.webhook_dlq_task.*": {"queue": "webhooks"},
        "workers.metrics_loop_task.*": {"queue": "default"},
        "workers.trend_scraper_task.*": {"queue": "default"},
        "workers.graph_execution_task.*": {"queue": "default"},
        "workers.rum_learning_task.*": {"queue": "default"},
    },
)

# Soporte para Celery Eager Mode en pytest
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() in ["true", "1"]:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
