"""
campaigns.py

Router para la Gestión de Campañas Comerciales en ViralSync (Fase 4A - Modo Campaña).
Ofrece CRUD de campañas para agrupar ideaciones, guiones y videos bajo un mismo objetivo.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from backend.db.daos import insert_campaign, get_campaigns_by_tenant
    from backend.db.session import get_async_db
    HAS_DAOS = True
except ImportError:
    HAS_DAOS = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Campañas"])


class CampaignCreateReq(BaseModel):
    name: str
    objective: Optional[str] = "Incrementar ventas y posicionamiento de marca"
    target_reels_count: Optional[int] = 8


@router.get("/{tenant_id}/campaigns")
async def list_campaigns(tenant_id: str):
    """
    Retorna la lista de campañas comerciales activas e históricas del tenant.
    """
    if not HAS_DAOS:
        raise HTTPException(status_code=503, detail="DAOs no disponibles.")

    try:
        rows = await get_campaigns_by_tenant(tenant_id)
        return [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "name": c.name,
                "objective": c.objective,
                "target_reels_count": c.target_reels_count,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in rows
        ]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error consultando campañas: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error al consultar las campañas del tenant."
        )


@router.post("/{tenant_id}/campaigns")
async def create_new_campaign(tenant_id: str, req: CampaignCreateReq):
    """
    Crea una nueva campaña comercial para agrupar las piezas del cliente.
    """
    if not HAS_DAOS:
        raise HTTPException(status_code=503, detail="DAOs no disponibles.")

    if not req.name.strip():
        raise HTTPException(status_code=400, detail="El nombre de la campaña es obligatorio.")

    try:
        row = await insert_campaign(
            tenant_id=tenant_id,
            name=req.name.strip(),
            objective=req.objective,
            target_reels_count=req.target_reels_count or 8,
        )
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "name": row.name,
            "objective": row.objective,
            "target_reels_count": row.target_reels_count,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error creando campaña: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error al crear la campaña."
        )
