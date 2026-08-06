"""
agents/mcp_servers/rag_mcp_server.py

Servidor MCP sobre Qdrant + LlamaIndex: memoria por tenant.

Cada tenant tiene su propio namespace/collection (aislamiento de datos,
ver AGENTS.md sección 1: "cada cliente tiene su propio namespace de
datos"). Expone:

  - personaje de marca (AGENTS.md 7.5) — se genera una vez en onboarding,
    se recupera en cada guion para mantener congruencia.
  - guiones/ideas ya clasificados Rojo/Amarillo/Verde (AGENTS.md 7.8) —
    alimenta la ideación del mes siguiente.
  - mapa de mercado (AGENTS.md 7.7) — errores/deseos/objeciones/creencias
    falsas, persistente por nicho.

Correr con: python -m agents.mcp_servers.rag_mcp_server
"""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Document

import os

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=QDRANT_URL)

mcp = FastMCP("rag-tools")


def _collection_name(tenant_id: str) -> str:
    # namespace por tenant — nunca compartir colección entre clientes
    return f"tenant_{tenant_id}"


def _get_index(tenant_id: str) -> VectorStoreIndex:
    vector_store = QdrantVectorStore(client=client, collection_name=_collection_name(tenant_id))
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)


@mcp.tool()
def obtener_personaje_marca(tenant_id: str) -> dict:
    """
    Recupera el personaje de marca persistido del tenant (AGENTS.md 7.5):
    3 palabras clave, elementos visuales recurrentes y objeto representativo.
    Se inyecta como contexto fijo en cada prompt de guion para congruencia.
    """
    index = _get_index(tenant_id)
    retriever = index.as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve("personaje_de_marca")
    if not nodes:
        return {}
    return nodes[0].metadata


@mcp.tool()
def guardar_personaje_marca(tenant_id: str, tres_palabras: list[str], elementos_visuales: list[str], objeto_representativo: str) -> dict:
    """Persiste el personaje de marca del tenant (se llama una vez, en onboarding)."""
    index = _get_index(tenant_id)
    doc = Document(
        text="personaje_de_marca",
        metadata={
            "tipo": "personaje_de_marca",
            "tres_palabras": tres_palabras,
            "elementos_visuales": elementos_visuales,
            "objeto_representativo": objeto_representativo,
        },
    )
    index.insert(doc)
    return {"status": "guardado"}


@mcp.tool()
def buscar_ideas_validadas(tenant_id: str, clasificacion: Literal["amarillo", "verde"], top_k: int = 5) -> list[dict]:
    """
    Devuelve ideas/guiones ya clasificados Amarillo o Verde (AGENTS.md 7.8)
    para reintentar en nuevos formatos el mes siguiente. La mayoría del
    volumen mensual de ideación debe partir de aquí, no de ideas 100%
    nuevas sin validar.
    """
    index = _get_index(tenant_id)
    retriever = index.as_retriever(
        similarity_top_k=top_k,
        filters={"clasificacion": clasificacion},
    )
    nodes = retriever.retrieve(f"ideas clasificacion {clasificacion}")
    return [n.metadata for n in nodes]


@mcp.tool()
def obtener_mapa_mercado(tenant_id: str, nicho: str) -> dict:
    """Recupera el mapa de mercado persistente del nicho (AGENTS.md 7.7)."""
    index = _get_index(tenant_id)
    retriever = index.as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve(f"mapa_mercado {nicho}")
    if not nodes:
        return {}
    return nodes[0].metadata


if __name__ == "__main__":
    mcp.run()
