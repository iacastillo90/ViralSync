"""
rag.py

Router para la exposición de la Biblioteca de Ganchos Ganadores (RAG Memory) al cliente (Fase 3B).
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger(__name__)

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
