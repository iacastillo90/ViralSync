"""
metrics_loop_task.py

Tarea Celery asíncrona para la captura y clasificación 80/20 a las 72h post-publicación.
Calcula el ratio de vistas/seguidores, clasifica en Rojo/Amarillo/Verde y ejecuta el bucle de auto-aprendizaje EMA RUM.
"""

import os
import logging
from typing import Dict, Any
from workers.celery_app import celery_app
from agents.criterion.rum_calculator import get_dynamic_threshold

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EMA_ALPHA = 0.15  # Peso de la nueva observación para evitar oscilaciones violentas


def update_niche_rum_threshold_ema(niche: str, actual_engagement_ratio: float) -> float:
    """Recalibración del umbral dinámico RUM por nicho usando Media Móvil Exponencial (EMA)."""
    current_threshold = get_dynamic_threshold(niche)
    
    # Normalizar ratio a escala de umbral RUM (rango objetivo 0.50 - 0.90)
    normalized_engagement = min(1.0, actual_engagement_ratio / 10.0)
    
    new_threshold = current_threshold + EMA_ALPHA * (normalized_engagement - current_threshold)
    clamped_threshold = max(0.50, min(0.90, round(new_threshold, 2)))

    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        r.set(f"rum_threshold:{niche}", str(clamped_threshold))
        logger.info(f"Bucle RUM Auto-Aprendizaje [{niche}]: Umbral actualizado de {current_threshold:.2f} -> {clamped_threshold:.2f}")
    except Exception as exc:
        logger.warning(f"No se pudo guardar el nuevo umbral RUM en Redis ({exc})")

    return clamped_threshold


@celery_app.task(name="workers.metrics_loop_task.audit_72h_metrics")
def audit_72h_metrics(tenant_id: str, video_id: str, views: int, followers: int, niche: str = "General") -> Dict[str, Any]:
    """
    Calcula el ratio relativo a las 72h, determina la clasificación 80/20 y recalibra el RUM por nicho.
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

    # Bucle RUM de Auto-Aprendizaje: Recalibrar umbral por nicho usando EMA
    new_niche_threshold = update_niche_rum_threshold_ema(niche, ratio)

    return {
        "tenant_id": tenant_id,
        "video_id": video_id,
        "niche": niche,
        "views_72h": views,
        "followers_at_publish": followers,
        "ratio": ratio,
        "classification": classification,
        "action_taken": action,
        "recalibrated_rum_threshold": new_niche_threshold,
    }
