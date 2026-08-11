"""
sse_manager.py

Administrador de conexiones Server-Sent Events (SSE) durable unificado.
Soporta Redis Pub/Sub, emisión directa (broadcast/publish) y utilidades helper para nodos del grafo.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, AsyncIterator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HEARTBEAT_SECONDS = 15

router = APIRouter(prefix="/realtime", tags=["realtime"])


class SSEManager:
    def __init__(self) -> None:
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
        self.start_redis_listener(tenant_id)
        return queue

    def start_redis_listener(self, tenant_id: str):
        """Inicia el listener de Redis Pub/Sub para retransmitir a colas locales (multi-replica)."""
        if self._redis_client:
            if not hasattr(self, "_active_subscribers"):
                self._active_subscribers = set()
            if tenant_id not in self._active_subscribers:
                self._active_subscribers.add(tenant_id)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._listen_redis_channel(tenant_id))
                except RuntimeError:
                    pass

    async def _listen_redis_channel(self, tenant_id: str):
        """Escucha redis.pubsub() en background para el canal sse:{tenant_id}."""
        try:
            import redis.asyncio as aioredis
            async_redis = aioredis.from_url(REDIS_URL, socket_timeout=1.0)
            pubsub = async_redis.pubsub()
            await pubsub.subscribe(f"sse:{tenant_id}")
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    if raw_data:
                        parsed = json.loads(raw_data)
                        event = parsed.get("event", "message")
                        data = parsed.get("data", {})
                        payload = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
                        if tenant_id in self._listeners:
                            for q in list(self._listeners[tenant_id]):
                                await q.put(payload)
        except Exception as exc:
            logger.debug(f"Redis PubSub listener finished for {tenant_id}: {exc}")

    def unsubscribe(self, tenant_id: str, queue: asyncio.Queue):
        """Desconecta al cliente de la cola de eventos del tenant."""
        if tenant_id in self._listeners and queue in self._listeners[tenant_id]:
            self._listeners[tenant_id].remove(queue)
            if not self._listeners[tenant_id]:
                del self._listeners[tenant_id]
                if hasattr(self, "_active_subscribers") and tenant_id in self._active_subscribers:
                    self._active_subscribers.remove(tenant_id)
        logger.info(f"SSE Cliente desconectado de tenant '{tenant_id}'")

    async def broadcast(self, tenant_id: str, event_type: str, data: dict):
        """Emite un evento SSE a todas las conexiones activas de un tenant."""
        await self.publish(tenant_id=tenant_id, event=event_type, data=data)

    async def emit_graph_error(self, tenant_id: str, message: str, code: str = None) -> None:
        """Emit un evento SSE ``graph_error`` con thread_id + mensaje.

        RESILIENCE-002: cuando el grafo falla en background tras responder 202,
        el frontend espera un evento SSE que nunca llegaba (sólo
        node_start/graph_complete). Este evento le permite conocer el fallo.

        D-D (REQ-PTT-03): ``code`` es ADITIVO — cuando el error lo expone
        (NoCandidatesError → "no_candidates") viaja en el payload para que el
        frontend distinga la causa; si es None NO se incluye (wire shape
        estable para eventos sin código).
        """
        data = {"thread_id": tenant_id, "message": message}
        if code is not None:
            data["code"] = code
        await self.broadcast(tenant_id, "graph_error", data)

    async def publish(self, tenant_id: str, event: str, data: Dict[str, Any]) -> None:
        """Emite un evento formateado vía Redis Pub/Sub y colas locales de memoria."""
        payload_dict = {"event": event, "data": data, "tenant_id": tenant_id}
        payload = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

        if self._redis_client:
            try:
                self._redis_client.publish(f"sse:{tenant_id}", json.dumps(payload_dict))
            except Exception as exc:
                logger.debug(f"PubSub local emission fallback ({exc})")

        if tenant_id in self._listeners:
            for queue in list(self._listeners[tenant_id]):
                await queue.put(payload)

    def publish_event(self, tenant_id: str, event: str, data: Dict[str, Any]) -> None:
        """Helper universal síncrono/asíncrono para publicar eventos SSE desde webhooks, workers o routers."""
        async def _pub():
            await self.publish(tenant_id, event, data)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_pub())
        except RuntimeError:
            asyncio.run(_pub())


sse_manager = SSEManager()



def _format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _event_generator(request: Request, tenant_id: str) -> AsyncIterator[str]:
    queue = sse_manager.subscribe(tenant_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                raw_payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                yield raw_payload if isinstance(raw_payload, str) else _format_sse(raw_payload["event"], raw_payload["data"])
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        sse_manager.unsubscribe(tenant_id, queue)


@router.get("/{tenant_id}/stream")
async def stream_tenant_events(tenant_id: str, request: Request):
    return StreamingResponse(
        _event_generator(request, tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def emit_node_progress(tenant_id: str, node_name: str, status: str) -> None:
    """Helper para emitir progreso desde nodos del grafo o workers síncronos de Celery."""
    labels = {
        "ideation": "Generando ideas RUM...",
        "human_approval_idea": "Esperando aprobación de idea",
        "scriptwriting": "Escribiendo guion...",
        "video_edit": "Editando y renderizando video...",
        "human_approval_publish": "Esperando aprobación de publicación",
        "publish": "Publicando...",
    }
    message = labels.get(node_name, node_name)

    async def _publish():
        await sse_manager.publish(
            tenant_id,
            event="node_progress",
            data={"node": node_name, "status": status, "message": message},
        )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_publish())
    except RuntimeError:
        asyncio.run(_publish())
