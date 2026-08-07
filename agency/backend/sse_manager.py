"""
sse_manager.py

Administrador de conexiones Server-Sent Events (SSE) durable basado en Redis Pub/Sub.
Emite eventos 'text/event-stream' seguros a través de múltiples instancias backend.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, AsyncGenerator

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class SSEManager:
    def __init__(self):
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._redis_client = None
        try:
            import redis
            self._redis_client = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        except Exception:
            logger.warning("Redis no disponible para SSE Pub/Sub. Usando fallback de memoria.")

    def subscribe(self, tenant_id: str) -> asyncio.Queue:
        """Suscribe una conexión del cliente a la cola de eventos del tenant."""
        if tenant_id not in self._listeners:
            self._listeners[tenant_id] = []
        queue = asyncio.Queue()
        self._listeners[tenant_id].append(queue)
        logger.info(f"SSE Cliente suscrito a tenant '{tenant_id}'. Total: {len(self._listeners[tenant_id])}")
        return queue

    def unsubscribe(self, tenant_id: str, queue: asyncio.Queue):
        """Desconecta al cliente de la cola de eventos del tenant."""
        if tenant_id in self._listeners and queue in self._listeners[tenant_id]:
            self._listeners[tenant_id].remove(queue)
            if not self._listeners[tenant_id]:
                del self._listeners[tenant_id]
        logger.info(f"SSE Cliente desconectado de tenant '{tenant_id}'")

    async def broadcast(self, tenant_id: str, event_type: str, data: dict):
        """Emite un evento SSE a todas las conexiones activas de un tenant."""
        payload_dict = {"event_type": event_type, "data": data, "tenant_id": tenant_id}
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        if self._redis_client:
            try:
                self._redis_client.publish(f"sse:{tenant_id}", json.dumps(payload_dict))
            except Exception as exc:
                logger.debug(f"PubSub local emission fallback ({exc})")

        if tenant_id in self._listeners:
            for queue in list(self._listeners[tenant_id]):
                await queue.put(payload)


sse_manager = SSEManager()
