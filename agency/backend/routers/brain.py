"""
brain.py

Router para el Cerebro de Marca / RAG (D5, REQ-API-3).
GET /api/v1/tenants/{tenant_id}/brain → objeto fabrica-free:

    {
        "tenant_id": <tid>,
        "status": "ok" | "no_data",
        "persona": {atributos de marca…} | null,
        "collection_stats": null,
        "chunks": [],
        "collection": "marketing_brain",
    }

persona proviene de la primera fila real de niches del tenant (el hogar real de
los atributos de marca — DDL 001 niches). NO se llama a Qdrant y NO se inventan
conteos de chunks (situación-portero "1240"). Sin filas → status "no_data" con
persona null. La protección Anti-IDOR se aplica a nivel de router desde main.py.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Niche
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Brain RAG"])

COLLECTION_NAME = "marketing_brain"


@router.get("/{tenant_id}/brain")
async def get_tenant_brain(
    tenant_id: str, db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Retorna el brain del tenant con persona real (niches) y cero datos fabricados."""
    persona = None

    if HAS_SQLALCHEMY and db is not None:
        try:
            result = await db.execute(
                select(Niche).where(Niche.tenant_id == tenant_id).limit(1)
            )
            niche_row = result.scalar_one_or_none()
            if niche_row:
                # D5: persona = el JSON de atributos de marca (personaje_marca_json)
                # de la primera fila de niches del tenant — el hogar real de los
                # atributos de marca según la DDL 001.
                persona = niche_row.personaje_marca_json
        except Exception as exc:
            logger.error(f"[{tenant_id}] Error al consultar brain en DB: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error temporal de base de datos al obtener el brain.",
            )

    return {
        "tenant_id": tenant_id,
        "status": "ok" if persona else "no_data",
        "persona": persona,
        "collection_stats": None,
        "chunks": [],
        "collection": COLLECTION_NAME,
    }