"""
competitors.py

Router de Cuentas Competidoras (S4 — REQ-COMP-01/02):
- GET  /api/v1/tenants/{tenant_id}/competitors             -> listado del tenant
- POST /api/v1/tenants/{tenant_id}/competitors             -> creación manual
  {platform, username, display_name, niche}
- PATCH /api/v1/tenants/{tenant_id}/competitors/{id}       -> toggle is_active
- POST /api/v1/tenants/{tenant_id}/competitors/{id}/ingest -> ingestión manual
  (SearXNG cache 6h -> extractor -> Qdrant con source="competitor")

El guard Anti-IDOR se aplica a nivel de router desde main.py
(dependencies=_TENANT_GUARD): todo endpoint queda protegido contra IDs ajenos.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import CompetitorAccount
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

    def get_async_db():
        return None

router = APIRouter(prefix="/api/v1/tenants", tags=["Competidores"])


class CompetitorCreateReq(BaseModel):
    platform: str = "instagram"
    username: str
    display_name: Optional[str] = None
    niche: Optional[str] = None


def _account_to_dict(account) -> Dict[str, Any]:
    """Proyección de una fila CompetitorAccount al contrato de la API (REQ-COMP-01)."""
    return {
        "id": account.id,
        "tenant_id": account.tenant_id,
        "platform": account.platform,
        "username": account.username,
        "display_name": account.display_name,
        "niche": account.niche,
        "is_active": account.is_active,
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


async def _get_account(db, tenant_id: str, account_id: str):
    """Devuelve la cuenta del tenant o None (404 honesto, nunca datos fabricados)."""
    return (
        await db.execute(
            select(CompetitorAccount).where(
                CompetitorAccount.id == account_id,
                CompetitorAccount.tenant_id == tenant_id,
            )
        )
    ).scalars().first()


@router.get("/{tenant_id}/competitors")
async def list_competitors(
    tenant_id: str,
    db=Depends(get_async_db),
) -> List[Dict[str, Any]]:
    """Lista las cuentas competidoras del tenant (activas e inactivas)."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        result = await db.execute(
            select(CompetitorAccount)
            .where(CompetitorAccount.tenant_id == tenant_id)
            .order_by(CompetitorAccount.created_at)
        )
        return [_account_to_dict(a) for a in result.scalars().all()]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error listando competidores: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al listar competidores.",
        )


@router.post("/{tenant_id}/competitors", status_code=status.HTTP_201_CREATED)
async def create_competitor(
    tenant_id: str,
    req: CompetitorCreateReq,
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """Crea manualmente una cuenta competidora (REQ-COMP-01/02)."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        account = CompetitorAccount(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            platform=req.platform or "instagram",
            username=req.username.strip(),
            display_name=(req.display_name or "").strip() or None,
            niche=(req.niche or "").strip() or None,
            is_active=True,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return _account_to_dict(account)
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error creando competidor: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al crear la cuenta competidora.",
        )


@router.patch("/{tenant_id}/competitors/{competitor_id}")
async def toggle_competitor(
    tenant_id: str,
    competitor_id: str,
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """Alterna el estado is_active de la cuenta (REQ-COMP-04 escenario 2)."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        account = await _get_account(db, tenant_id, competitor_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuenta competidora no encontrada o no pertenece al tenant.",
            )

        account.is_active = not account.is_active
        await db.commit()
        await db.refresh(account)
        return _account_to_dict(account)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error alternando competidor {competitor_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al alternar la cuenta competidora.",
        )


@router.post("/{tenant_id}/competitors/{competitor_id}/ingest")
async def ingest_competitor_account(
    tenant_id: str,
    competitor_id: str,
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """Dispara la ingestión manual (REQ-COMP-02): SearXNG -> extractor -> Qdrant."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        account = await _get_account(db, tenant_id, competitor_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuenta competidora no encontrada o no pertenece al tenant.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error leyendo competidor {competitor_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al leer la cuenta competidora.",
        )

    from backend.services.competitor_ingest import ingest_competitor

    count = await ingest_competitor(account)
    return {"account_id": account.id, "indexed_hooks": count}