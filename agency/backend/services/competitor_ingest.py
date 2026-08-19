"""
competitor_ingest.py

Servicio de ingestión de cuentas competidoras (S4 — Competitor Benchmark, REQ-COMP-02/03):
búsqueda SearXNG (cache 6h existente) -> extracción de estructura de ganchos ->
indexación en Qdrant `marketing_brain` con `source="competitor"` y `account_id`.

Solo se ingieren cuentas activas (REQ-COMP-04 escenario 2). El extractor de
estructura es una heurística determinista (sin LLM) para que el gap analysis del
benchmark sea estable y testeable sin dependencias.
"""

import logging
from typing import Dict, List, Any

from agents.mcp_servers.searxng_mcp_server import asearxng_search_sanitized
from backend.services.rag_context import index_winning_pattern

logger = logging.getLogger(__name__)

# Score viral base para hooks de competidores (determinista; sin métricas propias).
BASE_COMPETITOR_SCORE = 0.80

_NUMERIC_LIST_KEYWORDS = (
    "trucos",
    "formas",
    "errores",
    "tips",
    "razones",
    "señales",
    "habitos",
    "hábitos",
    "pasos",
)


def extract_hook_structure(title: str, snippet: str = "") -> Dict[str, str]:
    """
    Extrae y clasifica la estructura de un gancho a partir de título + snippet.

    Heurística determinista (sin LLM): devuelve {"title", "hook", "structure"}.
    El `hook` es el título (o el snippet si no hay título); la `structure` se
    clasifica por reglas de patrones virales comunes.
    """
    title = (title or "").strip()
    snippet = (snippet or "").strip()
    hook = title or snippet or "gancho viral"
    text = " ".join(part for part in (title, snippet) if part).strip()
    return {
        "title": title,
        "hook": hook,
        "structure": _classify_hook_structure(text),
    }


def _classify_hook_structure(text: str) -> str:
    """Clasifica la estructura de un gancho por reglas deterministas."""
    lowered = text.lower()
    tokens = lowered.split()

    if any(token.isdigit() for token in tokens[:3]) and any(
        keyword in lowered for keyword in _NUMERIC_LIST_KEYWORDS
    ):
        return "Lista Numérica + Valor Exclusivo"
    if "%" in lowered or "por ciento" in lowered or "de las personas" in lowered:
        return "Estadística / Porcentaje de Fricción"
    if "?" in lowered:
        return "Pregunta Retórica"
    if lowered.lstrip().startswith(
        ("stop", "deja de", "no hagas", "nunca hagas", "evita")
    ):
        return "Comando de Interrupción de Patrón"
    if any(keyword in lowered for keyword in ("secreto", "mito", "nadie te", "no sabes")):
        return "Revelación de Secreto / Curiosidad"
    if any(keyword in lowered for keyword in ("cómo", "haz esto", "mira esto")):
        return "Llamado a la Acción / Cómo"
    return "General / Storytelling"


async def ingest_competitor(account) -> int:
    """
    Ingiere los hooks virales de una cuenta competidora activa.

    Flujo: SearXNG (cache 6h, patrón existente) -> extractor de estructura ->
    `index_winning_pattern(..., source="competitor", account_id=...)` en Qdrant.

    Devuelve el número de hooks indexados. Cuentas inactivas o sin username se
    omiten sin llamar a SearXNG ni a Qdrant.
    """
    if not getattr(account, "is_active", False):
        logger.info(f"[{account.id}] Cuenta competidora inactiva; se omite la ingestión.")
        return 0

    username = (getattr(account, "username", None) or "").strip()
    if not username:
        logger.warning(f"[{account.id}] Cuenta competidora sin username; se omite la ingestión.")
        return 0

    niche = (getattr(account, "niche", None) or "").strip()
    query = f"{username} {niche} gancho viral".strip()
    logger.info(f"[{account.id}] Buscando hooks virales de {username} (cache SearXNG 6h)...")

    results: List[Dict[str, Any]] = await asearxng_search_sanitized(query, num_results=5)

    indexed = 0
    for item in results or []:
        title = (item.get("title") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        if not title and not snippet:
            continue

        hook_info = extract_hook_structure(title, snippet)
        ok = index_winning_pattern(
            tenant_id=getattr(account, "tenant_id", ""),
            pattern_text=hook_info["hook"],
            viral_score=BASE_COMPETITOR_SCORE,
            niche=niche,
            source="competitor",
            account_id=getattr(account, "id", None),
        )
        if ok:
            indexed += 1

    logger.info(f"[{account.id}] Ingestión de {username} completada: {indexed} hooks indexados.")
    return indexed
