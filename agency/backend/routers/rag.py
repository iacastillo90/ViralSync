"""
rag.py

Router para la exposición de la Biblioteca de Ganchos Ganadores (RAG Memory) al cliente (Fase 3B).
Incluye `GET /{tenant}/rag/benchmark` (S4 — REQ-COMP-04): comparación propios vs
competidores con top-N por similitud y gap analysis determinista por estructura.
"""

import logging
import math
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

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

router = APIRouter(prefix="/api/v1/tenants", tags=["Biblioteca RAG"])

_DEFAULT_HOOKS_BY_NICHE = [
  {
    "id": "hook_def_1",
    "pattern_text": "¿Sabías que el 90% de las personas comete este error en los primeros 5 segundos?",
    "viral_score": 0.94,
    "niche": "General",
    "structure": "Pregunta Retórica + Porcentaje de Fricción",
  },
  {
    "id": "hook_def_2",
    "pattern_text": "Stop de hacer esto si quieres lograr resultados profesionales hoy mismo.",
    "viral_score": 0.89,
    "niche": "General",
    "structure": "Comando de Interrupción de Patrón",
  },
  {
    "id": "hook_def_3",
    "pattern_text": "Este secreto cambió completamente la forma en que optimizamos nuestro contenido.",
    "viral_score": 0.88,
    "niche": "General",
    "structure": "Revelación Curiosidad / Transformación",
  },
  {
    "id": "hook_def_4",
    "pattern_text": "3 trucos rápidos que nadie te enseña para escalar sin presupuesto.",
    "viral_score": 0.86,
    "niche": "General",
    "structure": "Lista Numérica + Valor Exclusivo",
  },
  {
    "id": "hook_def_5",
    "pattern_text": "El mayor mito sobre el crecimiento orgánico en 2026 desmontado.",
    "viral_score": 0.85,
    "niche": "General",
    "structure": "Desmitificación + Urgencia",
  },
  {
    "id": "hook_def_6",
    "pattern_text": "Haz esto en tus próximos Reels y nota la diferencia en 24 horas.",
    "viral_score": 0.84,
    "niche": "General",
    "structure": "Llamado a la Acción Inmediato",
  },
]


@router.get("/{tenant_id}/rag/hooks")
async def get_rag_hooks(
    tenant_id: str,
    niche: str = "General",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Retorna la lista de ganchos ganadores indexados en Qdrant para el nicho seleccionado.
    """
    results = []

    try:
        from backend.services.rag_context import get_winning_patterns
        qdrant_patterns = get_winning_patterns(niche=niche, query="gancho viral", limit=limit)
        for idx, p in enumerate(qdrant_patterns):
            results.append({
                "id": f"qdrant_hook_{idx}",
                "pattern_text": p.get("pattern_text", ""),
                "viral_score": float(p.get("viral_score", 0.85)),
                "niche": p.get("niche", niche),
                "structure": "Patrón Aprendido RAG Memory",
            })
    except Exception as exc:
        logger.warning(f"[{tenant_id}] No se pudo consultar Qdrant RAG hooks: {exc}")

    # Si Qdrant tiene menos de los solicitados, complementar con la biblioteca estática
    if len(results) < limit:
        for def_hook in _DEFAULT_HOOKS_BY_NICHE:
            if len(results) >= limit:
                break
            results.append(def_hook)

    return results


# --------------------------------------------------------------------- #
# S4 — GET /{tenant}/rag/benchmark (REQ-COMP-04)
# --------------------------------------------------------------------- #


def _structure_of(payload: Dict[str, Any]) -> str:
    """Estructura del hook: payload explícito o clasificación determinista."""
    structure = payload.get("structure")
    if structure:
        return structure
    from backend.services.competitor_ingest import extract_hook_structure
    return extract_hook_structure(payload.get("pattern_text", ""), "")["structure"]


def _project_hook(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pattern_text": payload.get("pattern_text", ""),
        "structure": _structure_of(payload),
        "viral_score": float(payload.get("viral_score", 0.0)),
        "niche": payload.get("niche", ""),
        "source": payload.get("source", "own"),
        "account_id": payload.get("account_id"),
    }


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if not norm_a or not norm_b:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


async def _active_competitor_account_ids(db, tenant_id: str) -> set:
    """Ids de cuentas competidoras activas del tenant (REQ-COMP-04 escenario 2)."""
    if not HAS_SQLALCHEMY or db is None:
        return set()
    result = await db.execute(
        select(CompetitorAccount).where(
            CompetitorAccount.tenant_id == tenant_id,
            CompetitorAccount.is_active.is_(True),
        )
    )
    return {str(account.id) for account in result.scalars().all()}


@router.get("/{tenant_id}/rag/benchmark")
async def get_competitor_benchmark(
    tenant_id: str,
    niche: str = "General",
    limit: int = 5,
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Compara hooks propios (`source="own"` o legacy) vs competidores
    (`source="competitor"` y solo cuentas activas): top-N por similitud al query
    del nicho + gap analysis determinista por estructura (estructuras
    competidoras ausentes en las propias).
    """
    try:
        from backend.services.rag_context import get_winning_patterns, simple_embedding

        own_raw = get_winning_patterns(
            niche=niche, query="gancho viral", limit=limit, source="own"
        )
        comp_raw = get_winning_patterns(
            niche=niche, query="gancho viral", limit=limit, source="competitor"
        )

        active_ids = await _active_competitor_account_ids(db, tenant_id)
        comp_raw = [h for h in comp_raw if h.get("account_id") in active_ids]

        own_hooks = [_project_hook(h) for h in own_raw]
        competitor_hooks = [_project_hook(h) for h in comp_raw]

        query_vec = simple_embedding(f"{niche} gancho viral")
        scored = []
        for hook in comp_raw:
            hook_vec = simple_embedding(hook.get("pattern_text", "") or "default")
            projected = _project_hook(hook)
            projected["score"] = _cosine_similarity(hook_vec, query_vec)
            scored.append(projected)
        scored.sort(key=lambda item: item["score"], reverse=True)
        top_similar = scored[:limit]

        own_structures = {h["structure"] for h in own_hooks}
        competitor_structures = {h["structure"] for h in competitor_hooks}
        gaps = sorted(competitor_structures - own_structures)

        return {
            "own_hooks": own_hooks,
            "competitor_hooks": competitor_hooks,
            "top_similar": top_similar,
            "gaps": gaps,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"[{tenant_id}] No se pudo calcular el benchmark de competidores: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Error temporal al calcular el benchmark de competidores.",
        )
