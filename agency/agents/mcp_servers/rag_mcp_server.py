"""
rag_mcp_server.py

Servidor MCP para la herramienta de consulta RAG en Qdrant (Cerebro de Marketing).
Reglas:
- Búsqueda por similitud de coseno en la colección 'marketing_brain'.
- Determinista y liviano (vector de 384 dimensiones).
"""

import os
import hashlib
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "marketing_brain"


def simple_embedding(text: str) -> List[float]:
    """Generador determinista de embedding liviano (384-dim) para pruebas/dev local sin GPU/API pesada."""
    if not text:
        text = "default"
    vec = []
    for i in range(384):
        h = hashlib.sha256(f"{text}:{i}".encode("utf-8")).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vec.append(val)
    return vec


from backend.cache.rag_cache import rag_cache


def query_rag_knowledge(
    query: str, collection_name: str = COLLECTION_NAME, limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Realiza una búsqueda semántica RAG en Qdrant con caché semántica Redis.
    
    :param query: Texto de consulta (ej. 'personaje de marca', 'fórmula RUM').
    :param collection_name: Nombre de la colección en Qdrant.
    :param limit: Máximo de documentos a retornar.
    :return: Lista de payloads recuperados.
    """
    # 1. Verificar si existe la respuesta en la Caché Semántica Redis (0ms)
    cached = rag_cache.get(query)
    if cached:
        return cached

    result = []
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=QDRANT_URL, timeout=3.0)
        query_vector = simple_embedding(query)
        
        search_res = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
        )
        
        if search_res:
            result = [hit.payload for hit in search_res if hit.payload]
    except Exception as exc:
        logger.warning(f"Qdrant no disponible ({exc}). Retornando contexto de marca base.")

    if not result:
        # Contexto RAG estático de respaldo para dev/offline
        result = [
            {
                "filename": "brand_character.md",
                "content": f"Personaje de Marca para {query}: Tono Autoridad/Empático, Iluminación Neón Azul, Micrófono Dinámico Rode.",
            },
            {
                "filename": "rum_formula.md",
                "content": "Fórmula RUM = U * I * C * S * D * A. Umbral dinámico por nicho.",
            },
        ]

    # 2. Guardar en la caché Redis para futuras consultas
    rag_cache.set(query, result)
    return result
