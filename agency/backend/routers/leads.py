"""
leads.py

Router para la Calificación, Inbound Leads y Humano en el Bucle (Takeover).
Aislamiento Anti-IDOR Estricto: verifica que el tenant_id provino de un JWT verificado
antes de compararlo contra la URL. Nunca devuelve datos de ejemplo ante errores de DB.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Lead
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Leads Inbound"])


class TakeoverRequest(BaseModel):
    operator_id: str
    action: str = "pause_bot"


def _verify_tenant_access_fail_closed(request: Request, tenant_id: str):
    """
    Verificación de aislamiento de tenant Fail-Closed.

    Pasos:
    1. Exige que haya un usuario autenticado (request.state.authenticated_user), es decir,
       que el tenant_id provino de un JWT firmado — no de un header sin verificar.
    2. Verifica que el tenant_id del JWT coincida con el tenant_id de la URL.

    En AGENCY_ENV=dev, el campo authenticated_user puede no estar presente (testing local).
    En staging/prod, el middleware ya rechaza con 401 si no hay JWT válido, por lo que
    si se llega aquí sin authenticated_user es un error de configuración del middleware.
    """
    import os
    agency_env = os.getenv("AGENCY_ENV", "dev").lower()

    authenticated_user = getattr(request.state, "authenticated_user", None)

    # En staging/prod: si no hay usuario autenticado via JWT, cortar aquí
    if agency_env not in ("dev", "development") and not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida: se necesita un token JWT válido para acceder a este recurso.",
        )

    authenticated_tenant = getattr(request.state, "tenant_id", None)
    if not authenticated_tenant or authenticated_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado: Aislamiento Anti-IDOR violado para el tenant '{tenant_id}'.",
        )


@router.get("/{tenant_id}/leads")
async def get_tenant_leads(
    tenant_id: str, request: Request, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """Retorna los prospectos calificados consultando la base de datos ORM para el tenant autenticado."""
    _verify_tenant_access_fail_closed(request, tenant_id)

    if not HAS_SQLALCHEMY or db is None:
        # En dev sin DB configurada: lista vacía explícita (no datos de ejemplo)
        return []

    try:
        stmt = select(Lead).where(Lead.tenant_id == tenant_id)
        result = await db.execute(stmt)
        leads_orm = result.scalars().all()
        return [
            {
                "id": l.id,
                "tenant_id": l.tenant_id,
                "video_id": l.video_id,
                "keyword": l.keyword,
                "ig_user_id": l.ig_user_id,
                "mensaje_original": l.mensaje_original,
                "origen": l.origen,
                "calificado_at": l.calificado_at.isoformat() if l.calificado_at else None,
                "handled_by_human_at": l.handled_by_human_at.isoformat() if l.handled_by_human_at else None,
            }
            for l in leads_orm
        ]
    except Exception as exc:
        # Error de DB → 503 explícito. Nunca devolver datos de ejemplo que enmascaren el fallo.
        logger.error(f"[{tenant_id}] Error al consultar leads en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos. Por favor, intente de nuevo en unos momentos.",
        )


@router.post("/{tenant_id}/leads/{lead_id}/takeover")
async def takeover_lead(
    tenant_id: str, lead_id: str, req: TakeoverRequest, request: Request, db=Depends(get_async_db)
):
    """Pausa el bot de automatización y asigna la conversación a un operador humano consultando la DB."""
    _verify_tenant_access_fail_closed(request, tenant_id)

    if not HAS_SQLALCHEMY or db is None:
        from datetime import datetime, timezone
        return {
            "lead_id": lead_id,
            "tenant_id": tenant_id,
            "status": "handled_by_human",
            "handled_by_human_at": datetime.now(timezone.utc).isoformat(),
            "message": "Bot pausado. Operador asignado exitosamente (modo dev).",
        }


    try:
        stmt = select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id)
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead '{lead_id}' no encontrado para el tenant '{tenant_id}'.",
            )
        from datetime import datetime
        lead.status = "handled_by_human"
        lead.handled_by_human_at = datetime.utcnow()
        await db.commit()
        return {
            "lead_id": lead.id,
            "tenant_id": lead.tenant_id,
            "status": lead.status,
            "handled_by_human_at": lead.handled_by_human_at.isoformat(),
            "message": "Bot pausado. Operador asignado exitosamente.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error en takeover de lead '{lead_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al procesar el takeover. Por favor, intente de nuevo.",
        )
