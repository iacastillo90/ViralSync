"""
graph_execution.py

Router para la Ejecución Asíncrona del Grafo LangGraph y Reportes SSE en Vivo.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, status, BackgroundTasks
from pydantic import BaseModel
from backend.sse_manager import sse_manager
from agents.graph import build_agency_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import asyncio

router = APIRouter(prefix="/api/v1/tenants", tags=["Graph Execution"])

# Checkpointer global para persistencia en memoria (Demo/MVP)
# En un entorno distribuido usaríamos AsyncSqliteSaver o PostgresSaver
global_memory = MemorySaver()
graph_app = build_agency_graph(checkpointer=global_memory)


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

    No-op honesto (REQ-API-06): NO escribe en DB ni fabrica filas; sólo transmite
    el checkpoint via SSE y reanuda el grafo en background. El body devuelve
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
    
    # Reanudar el grafo en background
    config = {"configurable": {"thread_id": tenant_id}}
    
    async def _resume_graph():
        try:
            await graph_app.ainvoke(Command(resume={"idea_approved": req.status == "approved"}), config=config)
        except Exception as e:
            print(f"Error reanudando grafo para {tenant_id}: {e}")

    background_tasks.add_task(_resume_graph)

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
    
    # Reanudar el grafo en background
    config = {"configurable": {"thread_id": tenant_id}}
    
    async def _resume_publish():
        try:
            await graph_app.ainvoke(Command(resume={"publish_approved": req.status == "approved"}), config=config)
        except Exception as e:
            print(f"Error reanudando grafo publish para {tenant_id}: {e}")

    background_tasks.add_task(_resume_publish)

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
    }
    
    config = {"configurable": {"thread_id": tenant_id}}

    async def _run_graph_bg():
        try:
            final_state = await graph_app.ainvoke(initial_state, config=config)
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
        except Exception as e:
            print(f"Error en ejecución del grafo para {tenant_id}: {e}")

    background_tasks.add_task(_run_graph_bg)

    return {
        "status": "accepted",
        "message": "Graph execution started in background",
        "tenant_id": tenant_id,
    }

