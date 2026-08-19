"""
test_voice_personas_api.py

Pruebas TDD de Voice Personas (S2a — backend, slice API): T-S2a-04 (GET
/voice-personas activas con ambos voices por motor; PATCH /scripts/{id}/voice-persona
persiste) y T-S2a-05 (translate copia voice_persona_id al script LANG:XX y lo
expone en el dict — REQ-VOICE-04/05).

El seed se reproduce en la DB de test vía el modelo (las migraciones SQL no
corren sobre el SQLite de create_all) con los mismos valores confirmados en
design.md/proposal.md; aislado por UUID únicos por test (SQLite :memory:
compartido entre tests del mismo proceso). Seed compartido en
`_voice_personas_testdata.py`.
"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.main import app
from backend.security.auth import create_access_token
from backend.db.session import AsyncSessionLocal
from backend.db.models import Tenant, Script, Idea, VoicePersona
from _voice_personas_testdata import SEED_PERSONAS


def _auth_header(tenant_id: str) -> dict:
    token = create_access_token(
        user_id=f"user-voice-{tenant_id[:8]}", tenant_id=tenant_id, role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


async def _seed_personas(session) -> dict:
    """Inserta las 3 personas del seed (idempotente por name UNIQUE, igual que el
    ON CONFLICT DO NOTHING de la migración 012 — el SQLite :memory: compartido
    persiste entre tests del mismo proceso). Devuelve name -> VoicePersona."""
    rows = {}
    for name, cfg in SEED_PERSONAS.items():
        existing = (
            await session.execute(select(VoicePersona).where(VoicePersona.name == name))
        ).scalars().first()
        if existing:
            rows[name] = existing
            continue
        persona = VoicePersona(
            id=str(uuid.uuid4()),
            name=name,
            description=f"Persona {name}",
            edge_tts_voice=cfg["edge_tts_voice"],
            json2video_voice=cfg["json2video_voice"],
            locale_voices=dict(cfg["locale_voices"]),
            is_active=True,
        )
        session.add(persona)
        rows[name] = persona
    await session.commit()
    return rows


def _script_row(tenant_id: str, script_id: str, idea_id: str, **extra) -> Script:
    """Filas base repetidas en los tests de API (tenant + idea + script)."""
    return Script(
        id=script_id,
        tenant_id=tenant_id,
        idea_id=idea_id,
        gancho_0_5s="Gancho",
        contexto_5_30s="Contexto",
        moraleja_30_50s="Moraleja",
        cta_50_60s="CTA",
        **extra,
    )


@pytest.fixture
async def seeded_script(init_test_db):
    """Tenant + idea + script (sin persona) + seed idempotente de las 3 personas.
    Aislamiento por UUID únicos por test. Devuelve los ids y el mapa de personas."""
    tenant_id = str(uuid.uuid4())
    script_id = str(uuid.uuid4())
    idea_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        session.add(Tenant(id=tenant_id, name="Voice Tenant"))
        session.add(Idea(id=idea_id, tenant_id=tenant_id, texto="Idea de prueba"))
        session.add(_script_row(tenant_id, script_id, idea_id))
        rows = await _seed_personas(session)
        await session.commit()
    return {
        "tenant_id": tenant_id,
        "script_id": script_id,
        "idea_id": idea_id,
        "personas": rows,
    }


# ---------------------------------------------------------------------------
# T-S2a-04 — Router voice (GET /voice-personas, PATCH /scripts/{id}/voice-persona)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_voice_personas_lists_only_active_with_both_voices(seeded_script):
    """REQ-VOICE-01 + REQ-VOICE-04: GET /voice-personas devuelve exactamente las 3
    personas activas, cada una con edge_tts_voice y json2video_voice."""
    tenant_id = seeded_script["tenant_id"]
    async with AsyncSessionLocal() as session:
        # Una persona inactiva NO debe aparecer (filtro is_active=true).
        session.add(
            VoicePersona(
                id=str(uuid.uuid4()),
                name="Voz Inactiva",
                edge_tts_voice="es-MX-CecilioNeural",
                json2video_voice="es-MX-CecilioNeural",
                locale_voices={"es": "es-MX-CecilioNeural"},
                is_active=False,
            )
        )
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/api/v1/tenants/{tenant_id}/voice-personas",
            headers=_auth_header(tenant_id),
        )
    assert response.status_code == 200, f"Recibió {response.status_code}: {response.text}"
    personas = response.json()
    assert len(personas) == 3, f"Deben listarse exactamente 3 personas, recibió {len(personas)}"
    by_name = {p["name"]: p for p in personas}
    assert set(by_name) == set(SEED_PERSONAS)
    for p in personas:
        assert p["is_active"] is True
        assert p["edge_tts_voice"], f"{p['name']} debe exponer edge_tts_voice"
        assert p["json2video_voice"], f"{p['name']} debe exponer json2video_voice"


@pytest.mark.anyio
async def test_patch_script_voice_persona_persists(seeded_script):
    """REQ-VOICE-04: PATCH /scripts/{id}/voice-persona persiste voice_persona_id en el script."""
    tenant_id = seeded_script["tenant_id"]
    script_id = seeded_script["script_id"]
    persona_id = seeded_script["personas"]["Masculina Enérgica"].id

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/tenants/{tenant_id}/scripts/{script_id}/voice-persona",
            headers=_auth_header(tenant_id),
            json={"voice_persona_id": persona_id},
        )
    assert response.status_code == 200, f"Recibió {response.status_code}: {response.text}"
    assert response.json()["voice_persona_id"] == persona_id

    async with AsyncSessionLocal() as session:
        script = (
            await session.execute(select(Script).where(Script.id == script_id))
        ).scalars().one()
        assert script.voice_persona_id == persona_id


@pytest.mark.anyio
async def test_patch_script_voice_persona_unknown_persona_404(seeded_script):
    """REQ-VOICE-04: PATCH con persona inexistente devuelve 404 y no guarda nada.
    Primero valida que la ruta existe (PATCH válido -> 200), luego una persona
    desconocida -> 404 (el 404 proviene de la lógica, no de una ruta ausente)."""
    tenant_id = seeded_script["tenant_id"]
    script_id = seeded_script["script_id"]
    persona_id = seeded_script["personas"]["Masculina Enérgica"].id

    url = f"/api/v1/tenants/{tenant_id}/scripts/{script_id}/voice-persona"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ok = await ac.patch(
            url,
            headers=_auth_header(tenant_id),
            json={"voice_persona_id": persona_id},
        )
        assert ok.status_code == 200, "La ruta PATCH debe existir (sanity antes del 404)"
        response = await ac.patch(
            url,
            headers=_auth_header(tenant_id),
            json={"voice_persona_id": str(uuid.uuid4())},
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# T-S2a-05 — Translate preserva la persona (REQ-VOICE-05)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_translate_preserves_voice_persona(seeded_script, monkeypatch):
    """REQ-VOICE-05: POST /scripts/{id}/translate copia voice_persona_id al script
    nuevo (keyword=LANG:EN) y lo expone en el dict de respuesta."""
    import json as json_module

    tenant_id = seeded_script["tenant_id"]
    script_id = seeded_script["script_id"]
    persona_id = seeded_script["personas"]["Fundador Tech"].id

    # El script original tiene la persona asignada (escenario REQ-VOICE-05).
    async with AsyncSessionLocal() as session:
        script = (
            await session.execute(select(Script).where(Script.id == script_id))
        ).scalars().one()
        script.voice_persona_id = persona_id
        await session.commit()

    translated = json_module.dumps(
        {
            "gancho_0_5s": "Hook in English",
            "contexto_5_30s": "Context in English",
            "moraleja_30_50s": "Lesson in English",
            "cta_50_60s": "CTA in English",
            "keyword": "SOLICITUD",
        }
    )
    monkeypatch.setattr("agents.llm.acomplete", lambda **kwargs: translated)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{tenant_id}/scripts/{script_id}/translate",
            headers=_auth_header(tenant_id),
            json={"target_language": "en"},
        )
    assert response.status_code == 200, f"Recibió {response.status_code}: {response.text}"
    data = response.json()
    assert data["keyword"] == "LANG:EN"
    assert data["voice_persona_id"] == persona_id, (
        "El script traducido debe conservar la persona del original (REQ-VOICE-05)"
    )

    async with AsyncSessionLocal() as session:
        translated_script = (
            await session.execute(
                select(Script).where(Script.keyword == "LANG:EN")
            )
        ).scalars().one()
        assert translated_script.voice_persona_id == persona_id