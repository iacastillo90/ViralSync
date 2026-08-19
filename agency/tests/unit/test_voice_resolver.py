"""
test_voice_resolver.py

Pruebas TDD para el servicio voice_resolver (S2a, T-S2a-03 — REQ-VOICE-02/05):
resuelve la voz Edge-TTS de una persona según el idioma destino.

- lang "en" -> locale_voices["en"] (p. ej. en-US-ChristopherNeural para la
  persona Masculina Enérgica) — la voz del idioma destino (REQ-VOICE-05).
- lang "es" (default) -> locale_voices["es"] == edge_tts_voice.
- lang desconocido/sin mapeo -> fallback a edge_tts_voice (REQ-VOICE-02).
- lang_from_keyword: deriva el idioma desde script.keyword ("LANG:XX",
  default "es") — convención del flujo translate del diseño.

El servicio es puro (sin IO): construimos VoicePersona en memoria.
"""

from backend.db.models import VoicePersona
from backend.services.voice_resolver import resolve_voice, lang_from_keyword


def _persona(locale_voices=None, edge_voice="es-MX-JorgeNeural") -> VoicePersona:
    return VoicePersona(
        id="p1",
        name="Masculina Enérgica",
        edge_tts_voice=edge_voice,
        json2video_voice="es-MX-JorgeNeural",
        locale_voices=locale_voices or {"es": edge_voice, "en": "en-US-ChristopherNeural"},
        is_active=True,
    )


def test_resolve_voice_english_uses_locale_voice():
    """REQ-VOICE-05: lang=en devuelve la voz del idioma destino (en-US-ChristopherNeural)."""
    persona = _persona()
    assert resolve_voice(persona, "en") == "en-US-ChristopherNeural"


def test_resolve_voice_default_lang_es_uses_edge_voice():
    """REQ-VOICE-02: lang=es (default del catálogo) devuelve la voz Edge-TTS de la persona."""
    persona = _persona()
    assert resolve_voice(persona, "es") == "es-MX-JorgeNeural"
    assert resolve_voice(persona, None) == "es-MX-JorgeNeural"
    assert resolve_voice(persona, "") == "es-MX-JorgeNeural"


def test_resolve_voice_unknown_lang_falls_back_to_edge_voice():
    """REQ-VOICE-02: idioma sin mapeo en locale_voices cae al edge_tts_voice de la persona."""
    persona = _persona(locale_voices={"es": "es-MX-JorgeNeural"})  # sin "en"
    assert resolve_voice(persona, "en") == "es-MX-JorgeNeural"
    assert resolve_voice(persona, "fr") == "es-MX-JorgeNeural"


def test_resolve_voice_femenina_uses_jenny_for_english():
    """REQ-VOICE-05: triangulación — la persona Femenina Corporativa resuelve en->en-US-JennyNeural."""
    persona = VoicePersona(
        id="p2",
        name="Femenina Corporativa",
        edge_tts_voice="es-MX-DaliaNeural",
        json2video_voice="es-MX-DaliaNeural",
        locale_voices={
            "es": "es-MX-DaliaNeural",
            "es-MX": "es-MX-DaliaNeural",
            "es-ES": "es-ES-ElviraNeural",
            "en": "en-US-JennyNeural",
        },
        is_active=True,
    )
    assert resolve_voice(persona, "en") == "en-US-JennyNeural"
    assert resolve_voice(persona, "es-ES") == "es-ES-ElviraNeural"


def test_lang_from_keyword_derives_target_language():
    """REQ-VOICE-05: keyword 'LANG:EN' -> 'en'; sin prefijo LANG -> 'es'."""
    assert lang_from_keyword("LANG:EN") == "en"
    assert lang_from_keyword("LANG:PT") == "pt"
    assert lang_from_keyword("SOLICITUD") == "es"
    assert lang_from_keyword("") == "es"
    assert lang_from_keyword(None) == "es"