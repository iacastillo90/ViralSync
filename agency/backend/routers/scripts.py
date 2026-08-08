"""
scripts.py

Router para los Guiones 4 Bloques (REQ-API-2).
GET /api/v1/tenants/{tenant_id}/scripts → lista plana con los keys del DDL 001
de la tabla scripts; sin filas → 200 []; ante error de DB → 503 explícito
(nunca datos fabricados). La protección Anti-IDOR se aplica a nivel de router
desde main.py (dependencies=_TENANT_GUARD).
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Script
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Scripts 4 Bloques"])


def _script_to_dict(s) -> Dict[str, Any]:
    """Proyección de una fila Script a los keys del DDL 001 (design D3)."""
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "idea_id": s.idea_id,
        "gancho_0_5s": s.gancho_0_5s,
        "contexto_5_30s": s.contexto_5_30s,
        "moraleja_30_50s": s.moraleja_30_50s,
        "cta_50_60s": s.cta_50_60s,
        "keyword": s.keyword,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/{tenant_id}/scripts")
async def get_tenant_scripts(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """Retorna los guiones del tenant consultando la DB real. Sin datos → []; error → 503."""
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        result = await db.execute(select(Script).where(Script.tenant_id == tenant_id))
        scripts_orm = result.scalars().all()
        return [_script_to_dict(s) for s in scripts_orm]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consultar scripts en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al obtener scripts.",
        )