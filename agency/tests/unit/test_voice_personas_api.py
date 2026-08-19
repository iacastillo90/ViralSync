"""
test_voice_personas_api.py

Pruebas unitarias para las Voice Personas (Feature 2).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_list_voice_personas():
    from backend.routers.voice_personas import list_voice_personas

    personas = asyncio.run(list_voice_personas())
    assert isinstance(personas, list)
    assert len(personas) == 8
    assert "voice_code" in personas[0]


def test_set_tenant_voice_persona():
    from backend.routers.voice_personas import set_tenant_voice_persona, SetVoicePersonaReq

    mock_db = AsyncMock()
    mock_tenant = MagicMock()
    mock_tenant.id = "tenant_123"

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_tenant
    mock_db.execute.return_value = mock_res

    req = SetVoicePersonaReq(voice_code="es-MX-DaliaNeural", voice_name="Dalia")
    res = asyncio.run(set_tenant_voice_persona("tenant_123", req, db=mock_db))
    assert res["status"] == "success"
    assert res["voice_code"] == "es-MX-DaliaNeural"