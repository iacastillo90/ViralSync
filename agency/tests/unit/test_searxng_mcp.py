"""
test_searxng_mcp.py

Pruebas unitarias TDD para el servidor MCP de SearXNG (búsquedas sanitizadas).
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.mcp_servers.searxng_mcp_server import (
    sanitize_html_content,
    searxng_search_sanitized,
)


def test_sanitize_html_content_strips_tags():
    raw_html = "<p>Hola <b>Mundo</b>! <script>alert(1)</script></p>"
    clean = sanitize_html_content(raw_html)
    assert "<" not in clean
    assert ">" not in clean
    assert "Hola Mundo! alert(1)" in clean


def test_searxng_search_sanitized_fallback_when_offline():
    # Petición a URL inexistente dispara fallback estático
    results = searxng_search_sanitized("Negocios B2B", num_results=2)
    assert isinstance(results, list)
    assert len(results) == 2
    assert "title" in results[0]
    assert "snippet" in results[0]
    assert "url" in results[0]


def test_searxng_search_sanitized_mock_http():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "<h1>Título Test</h1>",
                "content": "<p>Snippet de prueba de búsqueda</p>",
                "url": "https://test.com",
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        results = searxng_search_sanitized("marketing SaaS", num_results=1)
        assert len(results) == 1
        assert results[0]["title"] == "Título Test"
        assert results[0]["snippet"] == "Snippet de prueba de búsqueda"
        assert results[0]["url"] == "https://test.com"
