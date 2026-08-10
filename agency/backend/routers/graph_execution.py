"""
graph_execution.py

Router para la Ejecución Asíncrona del Grafo LangGraph y Reportes SSE en Vivo.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, status, BackgroundTasks
from pydantic import BaseModel
from backend.sse_manager import sse_manager
from agents.graph import build_agency_graph
from backend.db.daos import update_idea_approval
from backend.db.checkpointer import build_checkpointer
from langgraph.types import Command
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["Graph Execution"])

# Checkpointer (design D2 / T-14): reemplazó el global MemorySaver. La factory
# decide — MemorySaver bajo FORCE_SQLITE=true (tests, PERSIST-04-2) o
# AsyncPostgresSaver sobre la conexión long-lived que abre el lifespan de
# main.py (PERSIST-04-1: thread_id=tenant_id, el estado sobrevive al restart).
# El grafo se construye lazy y main.py lo reconstruye tras `setup` del saver PG.
graph_app = None


def get_graph_app():
    """Devuelve el grafo compilado, construyéndolo con el checkpointer activo."""
    global graph_app
    if graph_app is None:
        graph_app = build_agency_graph(checkpointer=build_checkpointer())
    return graph_app


def rebuild_graph_app():
    """Reconstruye el grafo con un checkpointer nuevo (lifespan, T-14)."""
    global graph_app
    graph_app = build_agency_graph(checkpointer=build_checkpointer())
    return graph_app


def _thread_config(tenant_id: str) -> dict:
    """Configuración del checkpointer por thread (thread_id = tenant_id, PERSIST-04)."""
    return {"configurable": {"thread_id": tenant_id}}  # noqa: C408


async def _resume_graph_background(tenant_id: str, resume_payload: dict) -> None:
    """Reanuda un grafo pausado en background (RESILIENCE-002).

    Logea el resultado y, ante un fallo, emite un evento SSE ``graph_error`` con
    ``thread_id`` + mensaje para que el frontend no quede esperando eventos que
    nunca llegarán (sólo se emitían node_start/graph_complete).
    """
    config = _thread_config(tenant_id)
    try:
        await get_graph_app().ainvoke(Command(resume=resume_payload), config=config)
        logger.info("Graph resumed for tenant %s (resume payload: %s)", tenant_id, resume_payload)
    except Exception as exc:  # noqa: BLE001 - absence of logging means silent hang
        logger.error("Graph resume failed for tenant %s: %s", tenant_id, exc, exc_info=True)
        await sse_manager.emit_graph_error(tenant_id, str(exc))


async def _run_graph_background(tenant_id: str, initial_state: dict) -> None:
    """Ejecuta el grafo multi-agente en background (RESILIENCE-002).

    Idem ``_resume_graph_background``: broadcast de graph_complete en éxito o
    gráfica de error SSE en fallo.
    """
    config = _thread_config(tenant_id)
    try:
        final_state = await get_graph_app().ainvoke(initial_state, config=config)
        await sse_manager.broadcast(
            tenant_id,
            "graph_complete",
            {
                "node": "complete",
                "message": "Grafo ejecutado con éxito.",
                "final_state": {
                    "tenant_id": tenant_id,
                    "ideas_count": len(final_state.get("ideas", [])),
                },
            },
        )
        logger.info("Graph execution completed for tenant %s", tenant_id)
    except Exception as exc:  # noqa: BLE001 - absence of logging means silent hang
        logger.error("Graph execution failed for tenant %s: %s", tenant_id, exc, exc_info=True)
        await sse_manager.emit_graph_error(tenant_id, str(exc))


class GraphRunRequest(BaseModel):
    niche: Optional[str] = "B2B Software"
    niche_ppp: Optional[str] = "Escalar conversiones SaaS en 90 días"
    target_platform: Optional[str] = "instagram"
    # Credenciales OAuth del tenant para publicación. El frontend las pasa desde
    # la sesión del usuario. No se persisten en memoria del servidor.
    ig_user_id: Optional[str] = None
    ig_access_token: Optional[str] = None
    tiktok_access_token: Optional[str] = None
    youtube_access_token: Optional[str] = None
    # Datos de producto capturados en product-ingest (REQ-PERSIST-05 / D8): el
    # backend acepta product_image_url (y name/description opcionales) y
    # node_ideation persiste la fila `products` cuando la imagen viaja en state.
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_url: Optional[str] = None


class ProgressReportRequest(BaseModel):
    stage: str
    message: str
    percent: Optional[int] = 0


class IdeaApproveRequest(BaseModel):
    idea_id: str
    status: str = "approved"


class PublishApproveRequest(BaseModel):
    status: str = "approved"


@router.post("/{tenant_id}/progress")
async def report_progress(tenant_id: str, req: ProgressReportRequest):
    """Recibe reportes de progreso de microservicios externos y los transmite vía SSE al Frontend."""
    await sse_manager.broadcast(
        tenant_id,
        "render_progress",
        {
            "stage": req.stage,
            "message": req.message,
            "percent": req.percent,
            "tenant_id": tenant_id,
        },
    )
    return {"status": "broadcasted", "stage": req.stage, "percent": req.percent}


@router.post("/{tenant_id}/ideas/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_idea(tenant_id: str, req: IdeaApproveRequest, background_tasks: BackgroundTasks):
    """Checkpoint Humano: Aprobar o Rechazar Idea candidata y reanudar grafo.

    Commit real (REQ-PERSIST-03, design D4): además de transmitir el checkpoint
    via SSE y reanudar el grafo en background, ejecuta `UPDATE ideas SET
    approval_status=:st WHERE id=:idea_id AND tenant_id=:tenant_id` mediante el
    DAO — la DB, el grafo y la UI quedan de acuerdo (REQ-API-06 MODIFIED). Un
    idea_id no-UUID (p. ej. el id de e2e `"idea-e2e-001"`) actualiza 0 filas
    (no-op inofensivo, T-08 acceptance). El body devuelve
    `{"status":"accepted","kind":"idea_approval","queued":true}` con echo del
    idea_id real del request — nunca un id inventado.
    """
    await sse_manager.broadcast(
        tenant_id,
        "idea_checkpoint",
        {
            "idea_id": req.idea_id,
            "status": req.status,
            "tenant_id": tenant_id,
        },
    )

    # REQ-PERSIST-03 / T-12: UPDATE real de approval_status en la fila ideas.
    # si el id no matchea ninguna fila (no-UUID o de otro tenant) el DAO devuelve
    # False y el resume sigue igual: la UI ya no miente sobre el commit.
    updated = await update_idea_approval(tenant_id, req.idea_id, req.status)
    if not updated:
        logger.info(
            "approval affected 0 rows: idea_id=%s tenant=%s (id no-UUID or nonexistent)",
            req.idea_id,
            tenant_id,
        )

    # Reanudar el grafo en background (log + SSE graph_error ante fallo)
    background_tasks.add_task(
        _resume_graph_background,
        tenant_id,
        {"idea_approved": req.status == "approved"},
    )

    return {
        "status": "accepted",
        "kind": "idea_approval",
        "queued": True,
        "idea_id": req.idea_id,  # eco del id real, nunca fabricado
    }


@router.post("/{tenant_id}/publish/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_publish(tenant_id: str, req: PublishApproveRequest, background_tasks: BackgroundTasks):
    """Checkpoint Humano: Aprobar o Rechazar Publicación de Video y reanudar grafo.

    No-op honesto (D6, REQ-API-06): se eliminó el post_id fabricado
    `ig_reel_…_99812`. Devuelve 202 `{"status":"accepted","kind":"publish_approval",
    "queued":true}`; la tarjeta de aprobación de publicación se alimenta de la
    proveniencia real vía GET /scripts (no /videos existe).
    """
    await sse_manager.broadcast(
        tenant_id,
        "publish_checkpoint",
        {
            "status": req.status,
            "tenant_id": tenant_id,
        },
    )
    
    # Reanudar el grafo en background (log + SSE graph_error ante fallo)
    background_tasks.add_task(
        _resume_graph_background,
        tenant_id,
        {"publish_approved": req.status == "approved"},
    )

    return {
        "status": "accepted",
        "kind": "publish_approval",
        "queued": True,
    }


@router.post("/{tenant_id}/graph/run")
async def run_graph(tenant_id: str, req: GraphRunRequest, background_tasks: BackgroundTasks):
    """Ejecuta el grafo multi-agente asíncronamente."""
    await sse_manager.broadcast(
        tenant_id,
        "node_start",
        {"node": "ideation", "message": "Iniciando Agente de Ideación RUM...", "tenant_id": tenant_id},
    )

    initial_state = {
        "tenant_id": tenant_id,
        "niche": req.niche,
        "niche_ppp": req.niche_ppp,
        "target_platform": req.target_platform,
        # Credenciales OAuth necesarias para que node_publish no falle en producción.
        # Provienen directamente del request, nunca se almacenan en el servidor.
        "ig_user_id": req.ig_user_id,
        "ig_access_token": req.ig_access_token,
        "tiktok_access_token": req.tiktok_access_token,
        "youtube_access_token": req.youtube_access_token,
        "product_name": req.product_name,
        "product_description": req.product_description,
        "product_image_url": req.product_image_url,
    }
    
    # Ejecutar el grafo en background (log + SSE graph_error ante fallo)
    background_tasks.add_task(_run_graph_background, tenant_id, initial_state)

    return {
        "status": "accepted",
        "message": "Graph execution started in background",
        "tenant_id": tenant_id,
    }

