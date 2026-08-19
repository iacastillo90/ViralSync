"""
rag_context.py

Servicio de recuperación y almacenamiento de contexto RAG para el Cerebro de Marketing (Qdrant).

Ofrece:
1. `get_winning_patterns(niche, query, limit)`: Recupera patrones virales probados desde Qdrant ('marketing_brain').
2. `index_winning_pattern(tenant_id, pattern_text, viral_score, niche)`: Indexa nuevos patrones ganadores.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_raw_qdrant = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_URL = _raw_qdrant if _raw_qdrant.startswith("http://") or _raw_qdrant.startswith("https://") else f"http://{_raw_qdrant}"
COLLECTION_NAME = "marketing_brain"
VECTOR_DIM = 384


def simple_embedding(text: str) -> List[float]:
    """Generador determinista de embedding (384-dim) compatible con Qdrant."""
    import hashlib
    if not text:
        text = "default"
    vec = []
    for i in range(VECTOR_DIM):
        h = hashlib.sha256(f"{text}:{i}".encode("utf-8")).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vec.append(val)
    return vec


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL, timeout=3.0)


def _ensure_collection_exists(client) -> None:
    """Garantiza que la colección 'marketing_brain' exista en Qdrant."""
    try:
        from qdrant_client.http import models as rest_models
        collections = client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=rest_models.VectorParams(
                    size=VECTOR_DIM,
                    distance=rest_models.Distance.COSINE
                )
            )
            logger.info(f"Colección Qdrant '{COLLECTION_NAME}' creada con éxito.")
    except Exception as exc:
        logger.warning(f"No se pudo verificar/crear colección Qdrant: {exc}")


def index_winning_pattern(
    tenant_id: str,
    pattern_text: str,
    viral_score: float,
    niche: str = "",
    source: str = "own",
    account_id: Optional[str] = None,
) -> bool:
    """
    Indexa un patrón de guión o gancho de alta viralidad en la colección 'marketing_brain' de Qdrant.

    S4 (REQ-COMP-03): `source` distingue patrones propios ("own", default — compat
    con analytics_agent) de competidores ("competitor"); `account_id` vincula un
    patrón competidor a su cuenta para el filtro is_active del benchmark (REQ-COMP-04).
    """
    if not pattern_text:
        return False

    try:
        from qdrant_client.http import models as rest_models

        client = _get_qdrant_client()
        _ensure_collection_exists(client)

        point_id = str(uuid.uuid4())
        vector = simple_embedding(f"{niche} {pattern_text}")
        payload = {
            "id": point_id,
            "tenant_id": tenant_id,
            "pattern_text": pattern_text,
            "viral_score": float(viral_score),
            "niche": niche,
            "type": "winning_pattern",
            "source": source,
            "account_id": account_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                rest_models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )
        logger.info(f"[{tenant_id}] Patrón ganador indexado en Qdrant (Score={viral_score}): '{pattern_text[:50]}...'")
        return True
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error indexando patrón ganador en Qdrant: {exc}")
        return False


def get_winning_patterns(
    niche: str = "",
    query: str = "",
    limit: int = 3,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Consulta Qdrant recuperando los patrones de contenido con mayor rendimiento semántico para el nicho.

    S4 (REQ-COMP-04): con `source` se post-filtran los resultados por la fuente del
    payload — los patrones legacy (indexados por analytics_agent antes de S4, sin
    clave `source`) se consideran "own". Se recuperan más candidatos de Qdrant del
    límite pedido para que el filtrado no deje el resultado vacío por recorte.
    """
    search_text = f"{niche} {query}".strip() or "gancho viral contenido"
    results = []

    try:
        client = _get_qdrant_client()
        vector = simple_embedding(search_text)
        fetch_limit = limit * 4 if source is not None else limit
        search_res = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=fetch_limit,
        )
        if search_res:
            for hit in search_res:
                if not hit.payload:
                    continue
                item_source = hit.payload.get("source")
                if source is not None:
                    if item_source is None:
                        # Patrones indexados antes de S4 (analytics_agent) son propios.
                        if source != "own":
                            continue
                    elif item_source != source:
                        continue
                results.append(hit.payload)
    except Exception as exc:
        logger.warning(f"Error consultando Qdrant para patrones RAG ({exc}).")

    return results[:limit]
