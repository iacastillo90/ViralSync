"""
rag_cache.py

Caché Semántica RAG basada en Redis para ViralSync.
Evita consultas repetitivas de LLM / Qdrant para reglas fijas de RUM, PPP y marca,
retornando respuestas guardadas en memoria con latencia 0ms (TTL = 24h).
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DEFAULT_TTL = 86400  # 24 horas en segundos


class RAGSemanticCache:
    """Maneja el almacenamiento y recuperación en caché Redis de respuestas RAG."""

    def __init__(self):
        self._cache = {}  # Fallback en memoria si Redis no está disponible

    def _get_redis_client(self):
        try:
            import redis
            return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, socket_timeout=1.0)
        except Exception:
            return None

    def _hash_query(self, query: str) -> str:
        """Genera un hash MD5 único a partir del texto de consulta."""
        clean_q = query.strip().lower()
        return hashlib.md5(clean_q.encode("utf-8")).hexdigest()

    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Obtiene el contexto RAG desde la caché de Redis."""
        key = f"rag_cache:{self._hash_query(query)}"
        r = self._get_redis_client()

        if r:
            try:
                cached_bytes = r.get(key)
                if cached_bytes:
                    logger.info(f"CACHE HIT (Redis 0ms) para consulta RAG: '{query}'")
                    return json.loads(cached_bytes.decode("utf-8"))
            except Exception as exc:
                logger.warning(f"Error leyendo caché Redis ({exc}). Continuando...")

        if key in self._cache:
            logger.info(f"CACHE HIT (In-Memory 0ms) para consulta RAG: '{query}'")
            return self._cache[key]

        return None

    def set(self, query: str, value: List[Dict[str, Any]], ttl: int = DEFAULT_TTL):
        """Guarda la respuesta RAG en la caché Redis con un TTL determinado."""
        key = f"rag_cache:{self._hash_query(query)}"
        r = self._get_redis_client()

        if r:
            try:
                r.setex(key, ttl, json.dumps(value))
                logger.info(f"Respuesta RAG guardada en caché Redis por {ttl}s: '{query}'")
                return
            except Exception as exc:
                logger.warning(f"Error escribiendo en caché Redis ({exc})")

        self._cache[key] = value


rag_cache = RAGSemanticCache()
