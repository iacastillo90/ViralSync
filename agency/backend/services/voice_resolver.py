"""
voice_resolver.py

Servicio puro de resolución de voz (S2 — Voice Personas, REQ-VOICE-02/05):
dada una persona y un idioma destino, devuelve la voz Edge-TTS a usar en el
render. El idioma se deriva de la convención `script.keyword = "LANG:XX"` del
flujo translate (diseño D: resolver idioma desde keyword, sin campo nuevo).
Sin IO — testable unit sin DB (patrón trend_scorer.py).

- lang "es" (default): locale_voices["es"] == edge_tts_voice de la persona.
- lang con mapeo en locale_voices: devuelve esa voz (voz del idioma destino,
  REQ-VOICE-05).
- lang sin mapeo: fallback a edge_tts_voice (nunca rompe el render, REQ-VOICE-02).
"""

from typing import Optional

from backend.db.models import VoicePersona

DEFAULT_LANG = "es"


def lang_from_keyword(keyword: Optional[str]) -> str:
    """Deriva el idioma destino desde `script.keyword` ("LANG:XX"); default "es".

    Cualquier keyword sin el prefijo `LANG:` (o vacía) corresponde al idioma
    por defecto del catálogo de personas.
    """
    if not keyword:
        return DEFAULT_LANG
    prefix, sep, lang = keyword.partition(":")
    if sep and prefix.strip().upper() == "LANG":
        return lang.strip().lower() or DEFAULT_LANG
    return DEFAULT_LANG


def resolve_voice(persona: VoicePersona, lang: Optional[str]) -> str:
    """Devuelve la voz Edge-TTS de la persona para el idioma destino.

    Prioridad: `locale_voices[lang]` (búsqueda case-insensitive, p. ej. "es-ES")
    -> fallback a `edge_tts_voice` de la persona (la voz nativa del catálogo).
    `lang` vacío/None cae al default "es".
    """
    lang = (lang or DEFAULT_LANG).strip().lower()
    locale_voices = persona.locale_voices or {}
    for key, voice in locale_voices.items():
        if key.strip().lower() == lang and voice:
            return voice
    return persona.edge_tts_voice
