"""
workers/celery_app.py

Configuración principal de Celery con Redis broker.
En dev, se ejecuta con --concurrency=1 (AGENTS.md sección 8).
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "agency_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.video_edit_task", "workers.metrics_loop_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "1")),
)
