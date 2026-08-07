"""
graph_execution.py

Router para la Ejecución Asíncrona del Grafo LangGraph y Reportes SSE en Vivo.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel
from backend.sse_manager import sse_manager
from agents.graph import build_agency_graph

router = APIRouter(prefix="/api/v1/tenants", tags=["Graph Execution"])


class GraphRunRequest(BaseModel):
    niche: Optional[str] = "B2B Software"
    niche_ppp: Optional[str] = "Escalar conversiones SaaS en 90 días"


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


@router.post("/{tenant_id}/ideas/approve")
async def approve_idea(tenant_id: str, req: IdeaApproveRequest):
    """Checkpoint Humano: Aprobar o Rechazar Idea candidata."""
    await sse_manager.broadcast(
        tenant_id,
        "idea_checkpoint",
        {
            "idea_id": req.idea_id,
            "status": req.status,
            "tenant_id": tenant_id,
        },
    )
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "idea_id": req.idea_id,
        "idea_approval_status": req.status,
    }


@router.post("/{tenant_id}/publish/approve")
async def approve_publish(tenant_id: str, req: PublishApproveRequest):
    """Checkpoint Humano: Aprobar o Rechazar Publicación de Video."""
    published_post_id = f"ig_reel_{tenant_id[:8]}_99812"
    await sse_manager.broadcast(
        tenant_id,
        "publish_checkpoint",
        {
            "status": req.status,
            "published_post_id": published_post_id,
            "tenant_id": tenant_id,
        },
    )
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "publish_approval_status": req.status,
        "published_post_id": published_post_id,
    }


@router.post("/{tenant_id}/graph/run")
async def run_graph(tenant_id: str, req: GraphRunRequest):
    """Ejecuta el grafo multi-agente de ViralSync (Ideación -> Guion -> Director -> Render -> Publicación)."""
    await sse_manager.broadcast(
        tenant_id,
        "node_start",
        {"node": "ideation", "message": "Iniciando Agente de Ideación RUM...", "tenant_id": tenant_id},
    )

    graph_app = build_agency_graph()
    initial_state = {
        "tenant_id": tenant_id,
        "niche": req.niche,
        "niche_ppp": req.niche_ppp,
    }

    final_state = await graph_app.ainvoke(initial_state)

    await sse_manager.broadcast(
        tenant_id,
        "graph_complete",
        {
            "node": "complete",
            "message": "Grafo ejecutado con éxito.",
            "final_state": {
                "tenant_id": tenant_id,
                "ideas_count": len(final_state.get("approved_ideas", [])),
                "script": final_state.get("current_script"),
                "edited_video_uri": final_state.get("edited_video_uri"),
            },
        },
    )

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "ideas": final_state.get("approved_ideas", []),
        "script": final_state.get("current_script", {}),
        "edited_video_uri": final_state.get("edited_video_uri", ""),
    }

