"""
redis_cache.py

Servicio genérico de caché Redis para el ecosistema ViralSync (SearXNG, RAG, Trendings).
Soporta REDIS_URL o REDIS_HOST/REDIS_PORT con fallback in-memory ante desconexión.
"""

import os
import json
import logging
import hashlib
from typing import Any, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

_in_memory_store = {}


def _get_redis_client():
    try:
        import redis
        if REDIS_URL:
            return redis.Redis.from_url(REDIS_URL, socket_timeout=1.5)
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=1.5)
    except Exception:
        return None


def cache_get(key: str) -> Optional[Any]:
    """Obtiene un valor des-serializado de JSON desde la caché Redis (o in-memory fallback)."""
    r = _get_redis_client()
    if r:
        try:
            val = r.get(key)
            if val:
                return json.loads(val.decode("utf-8"))
        except Exception as exc:
            logger.debug(f"Redis cache_get fallback ({exc}) para key '{key}'")

    return _in_memory_store.get(key)


def cache_set(key: str, value: Any, ttl_seconds: int = 21600) -> bool:
    """Guarda un valor serializado como JSON en Redis con TTL (por defecto 6h = 21600s)."""
    r = _get_redis_client()
    serialized = json.dumps(value)
    if r:
        try:
            r.setex(key, ttl_seconds, serialized)
            return True
        except Exception as exc:
            logger.debug(f"Redis cache_set fallback ({exc}) para key '{key}'")

    _in_memory_store[key] = value
    return True


def hash_key(prefix: str, text: str) -> str:
    """Genera una clave con hash MD5 para caching."""
    clean = text.strip().lower()
    h = hashlib.md5(clean.encode("utf-8")).hexdigest()
    return f"{prefix}:{h}"
