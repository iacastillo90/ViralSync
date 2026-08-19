"""
test_voice_personas_core.py

Pruebas TDD de Voice Personas (S2a — backend, slice core): T-S2a-01 (migración
012: tabla voice_personas + scripts.voice_persona_id + seed idempotente de las 3
personas) y T-S2a-02 (modelos VoicePersona + Script.voice_persona_id).

Seed compartido en `_voice_personas_testdata.py` (un solo punto de verdad).
"""

from pathlib import Path

from backend.db.models import Script, VoicePersona
from _voice_personas_testdata import SEED_PERSONAS

_MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"
_MIGRATION_012 = _MIGRATIONS_DIR / "012_voice_personas.sql"


# ---------------------------------------------------------------------------
# T-S2a-01 — Migración 012 (contrato de archivo, patrón test_db_indexes de S1)
# ---------------------------------------------------------------------------


def test_migration_012_exists():
    """REQ-VOICE-01: la migración 012_voice_personas.sql existe."""
    assert _MIGRATION_012.exists(), "La migración 012_voice_personas.sql debe existir"


def test_migration_012_declares_voice_personas_table_and_script_column():
    """REQ-VOICE-01: la migración declara voice_personas (id, name UNIQUE, description,
    edge_tts_voice, json2video_voice, locale_voices JSONB, is_active) y
    scripts.voice_persona_id con FK a voice_personas."""
    sql = _MIGRATION_012.read_text()

    assert "CREATE TABLE IF NOT EXISTS voice_personas" in sql
    assert "name TEXT NOT NULL UNIQUE" in sql
    assert "edge_tts_voice TEXT NOT NULL" in sql
    assert "json2video_voice TEXT NOT NULL" in sql
    assert "locale_voices" in sql and "JSONB" in sql
    assert "is_active" in sql and "BOOLEAN" in sql
    assert "scripts ADD COLUMN IF NOT EXISTS voice_persona_id" in sql
    assert "REFERENCES voice_personas" in sql


def test_migration_012_seeds_exactly_three_personas():
    """REQ-VOICE-01: el seed idempotente inserta exactamente las 3 personas confirmadas,
    cada una con edge_tts_voice + json2video_voice y locale_voices para es/es-MX/es-ES/en."""
    sql = _MIGRATION_012.read_text()

    for name, cfg in SEED_PERSONAS.items():
        assert name in sql, f"El seed debe incluir la persona '{name}'"
        assert cfg["edge_tts_voice"] in sql
        assert cfg["json2video_voice"] in sql
        for lang, voice in cfg["locale_voices"].items():
            assert f'"{lang}"' in sql and voice in sql, (
                f"locale_voices de '{name}' debe mapear {lang} -> {voice}"
            )

    # Idempotencia (patrón IF NOT EXISTS de 002): ON CONFLICT DO NOTHING por name UNIQUE.
    assert "ON CONFLICT (name) DO NOTHING" in sql or "ON CONFLICT DO NOTHING" in sql


# ---------------------------------------------------------------------------
# T-S2a-02 — Modelos VoicePersona + Script.voice_persona_id
# ---------------------------------------------------------------------------


def test_voice_persona_model_maps_migration():
    """REQ-VOICE-01: el modelo VoicePersona declara las columnas de la migración 012."""
    table = VoicePersona.__table__
    assert "name" in table.c
    assert table.c.name.unique is True
    assert "edge_tts_voice" in table.c
    assert table.c.edge_tts_voice.nullable is False
    assert "json2video_voice" in table.c
    assert "locale_voices" in table.c
    assert "is_active" in table.c


def test_script_model_declares_voice_persona_id():
    """REQ-VOICE-04: el modelo Script declara voice_persona_id como FK a voice_personas."""
    script_table = Script.__table__
    assert "voice_persona_id" in script_table.c
    fk = list(script_table.c.voice_persona_id.foreign_keys)
    assert len(fk) == 1
    assert fk[0].target_fullname == "voice_personas.id"