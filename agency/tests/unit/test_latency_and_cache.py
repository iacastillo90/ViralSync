"""
test_latency_and_cache.py

Pruebas unitarias de contrato (TDD) para la Fase 1: Optimización de Latencia y Caché (REQ-LAT-01..03).
"""

import pytest
import yaml
import asyncio
from pathlib import Path
from agents.mcp_servers.searxng_mcp_server import asearxng_search_sanitized, searxng_search_sanitized


def test_asearxng_search_sanitized_returns_results():
    """REQ-LAT-01 / LAT-01-1: asearxng_search_sanitized es asíncrono y retorna resultados sanitizados."""
    results = asyncio.run(asearxng_search_sanitized("marketing digital b2b", num_results=2))
    assert isinstance(results, list)
    assert len(results) > 0
    for item in results:
        assert "title" in item
        assert "snippet" in item
        assert "url" in item
        assert len(item["snippet"]) <= 400



def test_searxng_search_sanitized_sync_wrapper():
    """Garantiza retrocompatibilidad con la función síncrona searxng_search_sanitized."""
    results = searxng_search_sanitized("estrategia contenido", num_results=2)
    assert isinstance(results, list)
    assert len(results) > 0


def test_litellm_production_config_has_cache():
    """REQ-LAT-03 / LAT-03-1: litellm_config.production.yaml incluye configuración de caché Redis."""
    config_path = Path(__file__).parents[2] / "gateway" / "litellm_config.production.yaml"
    assert config_path.exists(), "litellm_config.production.yaml debe existir"
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    litellm_settings = data.get("litellm_settings", {})
    assert "cache" in litellm_settings or "cache_type" in litellm_settings or "cache_params" in litellm_settings
