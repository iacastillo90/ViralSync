"""
rate_limiter.py

Módulo de Rate Limiting per-tenant e IP respaldado por Redis (REQ-RAT-01).
Protege endpoints de ejecución pesada de abuso de cuota LLM y flooding.
"""

import os
import logging
import redis

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client = None
try:
    _redis_client = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
except Exception as exc:
    logger.warning(f"Redis no disponible para Rate Limiting ({exc}). Deshabilitando limitador.")


def check_rate_limit(tenant_id: str, limit: int = 30, window_seconds: int = 60) -> bool:
    """Verifica si el tenant ha excedido el límite de peticiones en la ventana de tiempo.

    Retorna True si está permitido, False si excedió la cuota.
    """
    if not _redis_client:
        return True
    try:
        key = f"rate_limit:{tenant_id}"
        current = _redis_client.incr(key)
        if current == 1:
            _redis_client.expire(key, window_seconds)
        if current > limit:
            logger.warning(f"[{tenant_id}] Rate limit excedido: {current}/{limit} peticiones en {window_seconds}s")
            return False
        return True
    except Exception as exc:
        logger.debug(f"Rate limit check fallback ({exc})")
        return True


def reset_rate_limit(tenant_id: str) -> None:
    """Helper de test para reiniciar el contador de un tenant."""
    if _redis_client:
        try:
            _redis_client.delete(f"rate_limit:{tenant_id}")
        except Exception:
            pass
