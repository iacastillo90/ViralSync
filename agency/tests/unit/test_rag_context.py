"""
test_rag_context.py

Pruebas unitarias para la integración RAG de Qdrant (Fase 1A).
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.services.rag_context import simple_embedding, get_winning_patterns, index_winning_pattern


def test_simple_embedding_length_and_range():
    vec = simple_embedding("prueba gancho viral")
    assert len(vec) == 384
    assert all(-1.0 <= val <= 1.0 for val in vec)


def test_index_winning_pattern_success():
    with patch("backend.services.rag_context._get_qdrant_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_collections.return_value.collections = []

        res = index_winning_pattern(
            tenant_id="tenant_123",
            pattern_text="¿Sabías que el 90% de los podcast comete este error de audio?",
            viral_score=0.85,
            niche="Podcasting",
        )
        assert res is True
        assert mock_client.upsert.called


def test_get_winning_patterns_returns_payloads():
    with patch("backend.services.rag_context._get_qdrant_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        hit = MagicMock()
        hit.payload = {
            "pattern_text": "El secreto para duplicar tus ventas en Reels",
            "viral_score": 0.92,
        }
        mock_client.search.return_value = [hit]

        patterns = get_winning_patterns(niche="E-commerce", query="ventas", limit=1)
        assert len(patterns) == 1
        assert patterns[0]["viral_score"] == 0.92
