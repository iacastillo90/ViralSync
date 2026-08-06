"""
metrics_loop_task.py

Tarea Celery asíncrona para la captura y clasificación 80/20 a las 72h post-publicación.
Calcula el ratio de vistas/seguidores y clasifica en Rojo, Amarillo o Verde.
"""

import logging
from typing import Dict, Any
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.metrics_loop_task.audit_72h_metrics")
def audit_72h_metrics(tenant_id: str, video_id: str, views: int, followers: int) -> Dict[str, Any]:
    """
    Calcula el ratio relativo a las 72h y determina la clasificación 80/20.
    
    :param tenant_id: ID del tenant.
    :param video_id: ID del video publicado.
    :param views: Vistas alcanzadas a las 72h.
    :param followers: Seguidores de la cuenta al momento de publicar.
    :return: Diccionario con la clasificación y acción recomendada.
    """
    if followers <= 0:
        followers = 1  # Evitar división por cero

    ratio = round(views / followers, 2)

    if ratio < 1.0:
        classification = "ROJO"
        action = "Idea descartada. No generar variaciones."
    elif 1.0 <= ratio <= 10.0:
        classification = "AMARILLO"
        action = "Rendimiento aceptable. Encolado para 1 variación de gancho."
    else:
        classification = "VERDE"
        action = "Ganador viral. Encolado para 3 variaciones en próximo batch."

    logger.info(f"[{tenant_id}] Video '{video_id}' clasificado como {classification} (Ratio: {ratio})")

    return {
        "tenant_id": tenant_id,
        "video_id": video_id,
        "views_72h": views,
        "followers_at_publish": followers,
        "ratio": ratio,
        "classification": classification,
        "action_taken": action,
    }
