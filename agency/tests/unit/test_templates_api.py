"""
test_templates_api.py

Pruebas unitarias para las plantillas de nicho (Fase 3A).
"""

import asyncio
from backend.routers.templates import get_niche_templates


def test_get_niche_templates():
    templates = asyncio.run(get_niche_templates())
    assert isinstance(templates, list)
    assert len(templates) >= 1
    first = templates[0]
    assert "id" in first
    assert "name" in first
    assert "description" in first
