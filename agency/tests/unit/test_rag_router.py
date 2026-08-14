"""
test_rag_router.py

Pruebas unitarias para el router de la Biblioteca RAG de Ganchos Ganadores (Fase 3B).
"""

import asyncio
from backend.routers.rag import get_rag_hooks


def test_get_rag_hooks():
    hooks = asyncio.run(get_rag_hooks(tenant_id="tenant_123", niche="Podcasting", limit=5))
    assert isinstance(hooks, list)
    assert len(hooks) == 5
    first = hooks[0]
    assert "pattern_text" in first
    assert "viral_score" in first
