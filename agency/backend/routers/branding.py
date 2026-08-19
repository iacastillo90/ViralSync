"""
branding.py

Router backend para la personalización White-Label (Marca Blanca) por Agencia.
Permite configurar el logo, color primario y nombre comercial de la agencia.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select, update
from backend.db.models import Tenant
from backend.db.session import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["White Label Branding"])


class UpdateBrandingReq(BaseModel):
    agency_name: Optional[str] = "ViralSync Agency"
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#4F46E5"


@router.get("/{tenant_id}/branding")
async def get_tenant_branding(tenant_id: str, db=Depends(get_async_db)) -> Dict[str, Any]:
    """Obtiene la configuración de Marca Blanca activa del tenant."""
    try:
        res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado.")

        return {
            "tenant_id": tenant_id,
            "agency_name": getattr(tenant, "agency_name", None) or tenant.name,
            "logo_url": getattr(tenant, "logo_url", None) or "",
            "primary_color": getattr(tenant, "primary_color", None) or "#4F46E5",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error consultando branding: {exc}")
        return {
            "tenant_id": tenant_id,
            "agency_name": "Agencia ViralSync",
            "logo_url": "",
            "primary_color": "#4F46E5",
        }


@router.put("/{tenant_id}/branding")
async def update_tenant_branding(
    tenant_id: str,
    req: UpdateBrandingReq,
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Actualiza la identidad de marca blanca del tenant."""
    try:
        res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado.")

        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                agency_name=req.agency_name,
                logo_url=req.logo_url,
                primary_color=req.primary_color or "#4F46E5",
            )
        )
        await db.commit()

        logger.info(f"[{tenant_id}] Marca Blanca actualizada: {req.agency_name}")
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "agency_name": req.agency_name,
            "logo_url": req.logo_url,
            "primary_color": req.primary_color,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error actualizando branding: {exc}")
        raise HTTPException(status_code=500, detail="Error al actualizar marca blanca.")
