"""
backend/realtime/sse_manager.py

Streaming de estado en tiempo real hacia el dashboard (Next.js), vía
Server-Sent Events. Independiente del grafo de LangGraph: el backend
emite eventos ("Generando ideas...", "Esperando aprobación",
"Editando video...", "new_lead") a medida que un thread_id (=tenant_id)
avanza, evitando timeouts de REST en tareas largas (AGENTS.md sección 6).

Un canal por tenant. Multi-suscriptor: si el mismo Account Manager tiene
el dashboard abierto en dos pestañas, ambas reciben los eventos.

Endpoint FastAPI:
    GET /realtime/{tenant_id}/stream   -> text/event-stream

Publicación desde cualquier parte del backend/workers:
    await sse_manager.publish(tenant_id, event="node_started", data={...})
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/realtime", tags=["realtime"])

# Timeout de keepalive: SSE necesita un heartbeat periódico o algunos
# proxies/load balancers cortan la conexión por inactividad.
HEARTBEAT_SECONDS = 15


class SSEManager:
    def __init__(self) -> None:
        # tenant_id -> lista de colas, una por conexión abierta (multi-tab)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, tenant_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[tenant_id].append(queue)
        return queue

    def unsubscribe(self, tenant_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(tenant_id, [])
        if queue in subs:
            subs.remove(queue)
        if not subs:
            self._subscribers.pop(tenant_id, None)

    async def publish(self, tenant_id: str, event: str, data: dict[str, Any]) -> None:
        payload = {"event": event, "data": data}
        for queue in list(self._subscribers.get(tenant_id, [])):
            await queue.put(payload)


sse_manager = SSEManager()


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _event_generator(request: Request, tenant_id: str) -> AsyncIterator[str]:
    queue = await sse_manager.subscribe(tenant_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                yield _format_sse(payload["event"], payload["data"])
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"  # comentario SSE, mantiene viva la conexión
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
            "X-Accel-Buffering": "no",  # evita que nginx bufferee el stream
        },
    )


# --------------------------------------------------------------------------- #
# Helper para nodos del grafo: emitir progreso sin acoplar agents/ a FastAPI
# --------------------------------------------------------------------------- #

def emit_node_progress(tenant_id: str, node_name: str, status: str) -> None:
    """
    Llamado desde graph.py / workers de Celery al entrar/salir de cada nodo.
    Envuelve sse_manager.publish en una función sync-friendly ya que los
    nodos del grafo y las tasks de Celery no siempre corren en un loop
    async activo.
    """
    labels = {
        "ideation": "Generando ideas...",
        "human_approval_idea": "Esperando aprobación de idea",
        "scriptwriting": "Escribiendo guion...",
        "video_edit": "Editando video...",
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
