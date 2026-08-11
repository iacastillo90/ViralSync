"""
graph_execution.py

Router para la Ejecución Asíncrona del Grafo LangGraph y Reportes SSE en Vivo.
"""

from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, status, BackgroundTasks, HTTPException
from pydantic import BaseModel, field_validator
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
        # D-C/TCK-004: el checkpoint se reanuda con `Command(update=...)` (no
        # `resume=`) para que las flags de aprobación/rechazo del payload se
        # MERGEN en el estado del thread. Empíricamente (probe langgraph 1.2.10),
        # `Command(resume=...)` soltaba el payload en el nodo interrupt y el grafo
        # se re-pausaba para siempre sin entregar idea_approved/publish_rejected
        # a la ruta condicional. `Command(update=...)` entrega el estado y resume.
        await get_graph_app().ainvoke(Command(update=resume_payload), config=config)
        logger.info("Graph resumed for tenant %s (update payload: %s)", tenant_id, resume_payload)
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
        # D-C/TCK-005: guard isinstance — un final_state None (fake o caso raro)
        # NO crashea: sin broadcast y sin graph_error (acuerdo del test).
        if not isinstance(final_state, dict):
            logger.warning(
                "Graph execution returned non-dict final_state for tenant %s", tenant_id
            )
            return
        graph_complete_data = {
            "node": "complete",
            "message": "Grafo ejecutado con éxito.",
            "final_state": {
                "tenant_id": tenant_id,
                "ideas_count": len(final_state.get("ideas", [])),
            },
        }
        # D-C/TCK-005: `terminal_state` presente (p. ej. term_rejected) → campo
        # ADITIVO `terminal` en el payload para que el frontend distinga el fin
        # terminal del grafo. Ausente → wire shape estable sin la clave.
        terminal_state = final_state.get("terminal_state")
        if isinstance(terminal_state, str) and terminal_state:
            graph_complete_data["terminal"] = terminal_state
        await sse_manager.broadcast(tenant_id, "graph_complete", graph_complete_data)
        logger.info("Graph execution completed for tenant %s", tenant_id)
    except Exception as exc:  # noqa: BLE001 - absence of logging means silent hang
        logger.error("Graph execution failed for tenant %s: %s", tenant_id, exc, exc_info=True)
        # D-D/TCK-005: si el error expone `.code` (NoCandidatesError →
        # "no_candidates") viaja como campo aditivo; si no, call de 2 args
        # (wire estable, fakes compatibles con la firma original).
        code = getattr(exc, "code", None)
        if code is not None:
            await sse_manager.emit_graph_error(tenant_id, str(exc), code=code)
        else:
            await sse_manager.emit_graph_error(tenant_id, str(exc))


class GraphRunRequest(BaseModel):
    niche: Optional[str] = "B2B Software"
    niche_ppp: Optional[str] = "Escalar conversiones SaaS en 90 días"
    target_platform: Optional[str] = "instagram"
    ig_user_id: Optional[str] = None
    ig_access_token: Optional[str] = None
    tiktok_access_token: Optional[str] = None
    youtube_access_token: Optional[str] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_url: Optional[str] = None
    product_object_key: Optional[str] = None

    @field_validator("ig_access_token", "tiktok_access_token", "youtube_access_token", mode="after")
    @classmethod
    def validate_oauth_tokens(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("El token de acceso OAuth no puede estar vacío o contener solo espacios.")
            if len(stripped) < 5:
                raise ValueError("El token de acceso OAuth debe tener al menos 5 caracteres.")
            return stripped
        return v


class ProgressReportRequest(BaseModel):
    stage: str
    message: str
    percent: Optional[int] = 0


class IdeaApproveRequest(BaseModel):
    idea_id: str
    # D-E (REQ-PTT-04): allowlist — status libre era una puerta abierta; fuera
    # de {approved, rejected} FastAPI responde 422 y el handler jamás corre
    # (ni commit ni resume).
    status: Literal["approved", "rejected"] = "approved"


class PublishApproveRequest(BaseModel):
    status: Literal["approved", "rejected"] = "approved"


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
    DAO — la DB, el grafo y la UI quedan de acuerdo (REQ-API-06 MODIFIED).

    D-E (REQ-PTT-04): el UPDATE va PRIMERO y su bool decide. 0 filas (id
    unknown/stale/no-UUID) → 404 HONESTO antes de broadcast + resume: un
    no-op nunca puede parecer progreso. `status` está allowlisteado en el
    modelo ({approved, rejected}) → cualquier otra cosa es 422 sin efectos.
    El body devuelve `{"status":"accepted","kind":"idea_approval",
    "queued":true}` con echo del idea_id real del request — nunca un id
    inventado.
    """
    # D-E: UPDATE antes de transmitir — el DAO devuelve True sólo si actualizó
    # exactamente 1 fila de ESTE tenant (precedente: update_video_publish).
    updated = await update_idea_approval(tenant_id, req.idea_id, req.status)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="idea not found or stale",
        )

    await sse_manager.broadcast(
        tenant_id,
        "idea_checkpoint",
        {
            "idea_id": req.idea_id,
            "status": req.status,
            "tenant_id": tenant_id,
        },
    )

    # D-B: payload con AMBAS señales positivas (idea_approved / idea_rejected)
    # para que la ruta condicional del grafo distinga "decidido" de "no
    # decidido" — nunca conflaciona rejected con not-yet (D-B).
    payload = {
        "idea_approved": req.status == "approved",
        "idea_rejected": req.status == "rejected",
    }
    try:
        from workers.graph_execution_task import resume_graph_task
        resume_graph_task.delay(tenant_id, payload)
    except Exception as exc:
        logger.warning("Celery dispatch failed for resume_graph (%s), falling back to background_tasks", exc)
        background_tasks.add_task(_resume_graph_background, tenant_id, payload)

    return {
        "status": "accepted",
        "kind": "idea_approval",
        "queued": True,
        "idea_id": req.idea_id,  # eco del id real, nunca fabricado
    }


@router.post("/{tenant_id}/publish/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_publish(tenant_id: str, req: PublishApproveRequest, background_tasks: BackgroundTasks):
    """Checkpoint Humano: Aprobar o Rechazar Publicación de Video y reanudar grafo."""
    await sse_manager.broadcast(
        tenant_id,
        "publish_checkpoint",
        {
            "status": req.status,
            "tenant_id": tenant_id,
        },
    )
    
    payload = {
        "publish_approved": req.status == "approved",
        "publish_rejected": req.status == "rejected",
    }
    try:
        from workers.graph_execution_task import resume_graph_task
        resume_graph_task.delay(tenant_id, payload)
    except Exception as exc:
        logger.warning("Celery dispatch failed for resume_publish (%s), falling back to background_tasks", exc)
        background_tasks.add_task(_resume_graph_background, tenant_id, payload)

    return {
        "status": "accepted",
        "kind": "publish_approval",
        "queued": True,
    }


@router.post("/{tenant_id}/graph/run")
async def run_graph(tenant_id: str, req: GraphRunRequest, background_tasks: BackgroundTasks):
    """Ejecuta el grafo multi-agente asíncronamente."""
    from backend.security.rate_limiter import check_rate_limit
    if not check_rate_limit(tenant_id, limit=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit excedido para este tenant. Intente nuevamente en 60 segundos.",
            headers={"Retry-After": "60"},
        )

    if req.product_object_key and not req.product_object_key.startswith(f"{tenant_id}/"):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="product_object_key outside tenant prefix",
        )

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
        "ig_user_id": req.ig_user_id,
        "ig_access_token": req.ig_access_token,
        "tiktok_access_token": req.tiktok_access_token,
        "youtube_access_token": req.youtube_access_token,
        "product_name": req.product_name,
        "product_description": req.product_description,
        "product_image_url": req.product_image_url,
        "product_object_key": req.product_object_key,
    }
    
    try:
        from workers.graph_execution_task import run_graph_task
        run_graph_task.delay(tenant_id, initial_state)
    except Exception as exc:
        logger.warning("Celery dispatch failed for run_graph (%s), falling back to background_tasks", exc)
        background_tasks.add_task(_run_graph_background, tenant_id, initial_state)

    return {
        "status": "accepted",
        "message": "Graph execution started in background",
        "tenant_id": tenant_id,
    }


