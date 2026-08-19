"""
leads.py

Router para la Calificación, Inbound Leads y Humano en el Bucle (Takeover).
Aislamiento Anti-IDOR Estricto: verifica que el tenant_id provino de un JWT verificado
antes de compararlo contra la URL. Nunca devuelve datos de ejemplo ante errores de DB.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Lead
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

    def get_async_db():
        return None

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


def _extract_intent_from_history(conversacion_history: Optional[str]) -> Optional[str]:
    """Extrae el intent de la última clasificación persistida (T-S1-08, REQ-DM-LEAD-01)."""
    if not conversacion_history:
        return None
    try:
        history = json.loads(conversacion_history)
        if isinstance(history, list) and history:
            return history[-1].get("intent")
    except (ValueError, TypeError):
        pass
    return None


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
                "id": lead.id,
                "tenant_id": lead.tenant_id,
                "video_id": lead.video_id,
                "keyword": lead.keyword,
                "ig_user_id": lead.ig_user_id,
                "mensaje_original": lead.mensaje_original,
                "origen": lead.origen,
                "status": lead.status,
                "qualification_score": lead.qualification_score,
                "intent": _extract_intent_from_history(lead.conversacion_history),
                "calificado_at": lead.calificado_at.isoformat() if lead.calificado_at else None,
                "handled_by_human_at": lead.handled_by_human_at.isoformat() if lead.handled_by_human_at else None,
            }
            for lead in leads_orm
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
