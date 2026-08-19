"""
competitor_mining.py

Router backend para la Minería de Tendencias de Competidores (Feature 5).
Permite analizar URLs o marcas competidoras e indexar sus patrones en la memoria RAG Qdrant.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, status
from backend.services.competitor_miner import extract_competitor_viral_patterns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["Competitor Mining"])


class MineCompetitorReq(BaseModel):
    competitor_url_or_topic: str
    niche: Optional[str] = "General"


@router.post("/{tenant_id}/competitor-mine")
async def mine_competitor_trends(tenant_id: str, req: MineCompetitorReq) -> Dict[str, Any]:
    """Extrae patrones virales de competidores e inyecta los ganchos en la memoria Qdrant."""
    if not req.competitor_url_or_topic.strip():
        raise HTTPException(status_code=400, detail="Debe ingresar una URL o tema de competidor.")

    try:
        patterns = extract_competitor_viral_patterns(
            niche=req.niche or "General",
            competitor_query=req.competitor_url_or_topic.strip()
        )
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "patterns_extracted": len(patterns),
            "patterns": patterns,
        }
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error minando competidor: {exc}")
        raise HTTPException(status_code=500, detail="Error en la minería de tendencias.")
