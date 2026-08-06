"""
test_rag_mcp.py

Pruebas unitarias TDD para el servidor MCP de RAG (Qdrant).
"""

import pytest
from agents.mcp_servers.rag_mcp_server import (
    simple_embedding,
    query_rag_knowledge,
)


def test_simple_embedding_length_and_range():
    vec = simple_embedding("personaje de marca")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(-1.0 <= v <= 1.0 for v in vec)


def test_query_rag_knowledge_fallback_when_offline():
    # Petición cuando Qdrant no está corriendo debe retornar contexto fallback determinista
    results = query_rag_knowledge("personaje de marca")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "content" in results[0]
