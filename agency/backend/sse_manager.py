"""
sse_manager.py

Administrador de conexiones Server-Sent Events (SSE) para tiempo real.
Emite eventos formateados como 'text/event-stream' para consumir en el frontend Next.js vía Zustand.
"""

import json
import asyncio
import logging
from typing import Dict, List, AsyncGenerator

logger = logging.getLogger(__name__)


class SSEManager:
    def __init__(self):
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

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
        if tenant_id not in self._listeners:
            return

        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for queue in list(self._listeners[tenant_id]):
            await queue.put(payload)


sse_manager = SSEManager()
