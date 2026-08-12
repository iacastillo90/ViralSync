"""
ideas.py

Router para las Ideas Candidatas (D3, REQ-API-1).
GET /api/v1/tenants/{tenant_id}/ideas → lista plana con todos los keys del DDL 001
de la tabla ideas; sin filas → 200 []; ante error de DB → 503 explícito.
Nunca devuelve filas fabricadas. La protección Anti-IDOR se aplica a nivel de
router desde main.py (dependencies=_TENANT_GUARD).
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Idea
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Ideas Candidatas"])


def _idea_to_dict(i) -> Dict[str, Any]:
    """Proyección de una fila Idea a todos los keys del DDL 001 (design D3)."""
    return {
        "id": i.id,
        "tenant_id": i.tenant_id,
        "niche_id": i.niche_id,
        "texto": i.texto,
        "gancho": i.gancho,
        "entendible_nino_5_anos": i.entendible_nino_5_anos,
        "interesa_50_de_100": i.interesa_50_de_100,
        "universalidad": float(i.universalidad) if i.universalidad is not None else None,
        "intensidad": float(i.intensidad) if i.intensidad is not None else None,
        "claridad": float(i.claridad) if i.claridad is not None else None,
        "shareability": float(i.shareability) if i.shareability is not None else None,
        "distribucion": float(i.distribucion) if i.distribucion is not None else None,
        "alineacion": float(i.alineacion) if i.alineacion is not None else None,
        "rum_score": float(i.rum_score) if i.rum_score is not None else None,
        "rum_threshold_id": i.rum_threshold_id,
        "passes_threshold": i.passes_threshold,
        "approval_status": i.approval_status,
        "origen_reintento_de": i.origen_reintento_de,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@router.get("/{tenant_id}/ideas")
async def get_tenant_ideas(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """Retorna las ideas del tenant consultando la DB real. Sin datos → []; error → 503."""
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        result = await db.execute(
            select(Idea).where(Idea.tenant_id == tenant_id).order_by(Idea.created_at.desc())
        )
        ideas_orm = result.scalars().all()
        return [_idea_to_dict(i) for i in ideas_orm]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consultar ideas en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al obtener ideas.",
        )