"""
leads.py

Router para la Calificación, Inbound Leads y Humano en el Bucle (Takeover).
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/tenants", tags=["Leads Inbound"])


class TakeoverRequest(BaseModel):
    operator_id: str
    action: str = "pause_bot"


@router.get("/{tenant_id}/leads")
async def get_tenant_leads(tenant_id: str) -> List[Dict[str, Any]]:
    """Retorna los prospectos calificados capturados en las respuestas de Instagram."""
    return [
        {
            "id": "lead-001",
            "tenant_id": tenant_id,
            "video_id": "video-55",
            "keyword": "CONSULTA",
            "ig_user_id": "user_ig_9921",
            "mensaje_original": "Hola! Quiero la CONSULTA por favor",
            "origen": "comment",
            "calificado_at": "2026-08-06T01:45:00Z",
            "handled_by_human_at": None,
        }
    ]


@router.post("/{tenant_id}/leads/{lead_id}/takeover")
async def takeover_lead(tenant_id: str, lead_id: str, req: TakeoverRequest):
    """Pausa el bot de automatización y asigna la conversación a un operador humano."""
    return {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "status": "handled_by_human",
        "handled_by_human_at": "2026-08-06T02:30:00Z",
        "message": "Bot pausado. Operador asignado exitosamente.",
    }
