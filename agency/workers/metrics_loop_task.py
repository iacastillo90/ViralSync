"""
workers/metrics_loop_task.py

Tarea de Celery para monitoreo de métricas a 72h y clasificación Rojo/Amarillo/Verde.
(AGENTS.md sección 7.8)
"""

import logging
from datetime import datetime, timezone
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.metrics_loop_task.evaluate_video_metrics_72h")
def evaluate_video_metrics_72h(tenant_id: str, video_id: str, views_72h: int, followers_count: int) -> dict:
    logger.info(f"[Tenant {tenant_id}] Evaluando métricas 72h para video {video_id}")
    
    if followers_count <= 0:
        followers_count = 1

    ratio = views_72h / followers_count

    if ratio < 1.0:
        classification = "rojo"
        action = "Descartar idea y estructura."
    elif ratio < 10.0:
        classification = "amarillo"
        action = "Reintentar el mes siguiente en 1-2 formatos distintos (mismo ángulo)."
    else:
        classification = "verde"
        action = "Reintentar en 2-3 formatos distintos. Prioridad máxima para ideación."

    result = {
        "tenant_id": tenant_id,
        "video_id": video_id,
        "views_72h": views_72h,
        "followers_at_publish": followers_count,
        "ratio": round(ratio, 2),
        "classification": classification,
        "action_recommended": action,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Video {video_id} clasificado como '{classification.upper()}' (Ratio: {ratio:.2f})")
    return result
