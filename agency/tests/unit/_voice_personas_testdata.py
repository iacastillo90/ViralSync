"""
_voice_personas_testdata.py

Datos compartidos de Voice Personas (S2a) para los archivos de test
(test_voice_personas_core.py — migración/modelos, test_voice_personas_api.py —
endpoints). Un solo punto de verdad del seed confirmado en proposal
(Resolved Decisions #2) y design/migrations/012.

No es un módulo de test (prefijo `_`): pytest no lo recolecta.
"""

# Seed confirmado por el usuario (proposal Resolved Decisions #2 + design 012).
SEED_PERSONAS = {
    "Masculina Enérgica": {
        "edge_tts_voice": "es-MX-JorgeNeural",
        "json2video_voice": "es-MX-JorgeNeural",
        "locale_voices": {
            "es": "es-MX-JorgeNeural",
            "es-MX": "es-MX-JorgeNeural",
            "es-ES": "es-ES-AlvaroNeural",
            "en": "en-US-ChristopherNeural",
        },
    },
    "Femenina Corporativa": {
        "edge_tts_voice": "es-MX-DaliaNeural",
        "json2video_voice": "es-MX-DaliaNeural",
        "locale_voices": {
            "es": "es-MX-DaliaNeural",
            "es-MX": "es-MX-DaliaNeural",
            "es-ES": "es-ES-ElviraNeural",
            "en": "en-US-JennyNeural",
        },
    },
    "Fundador Tech": {
        "edge_tts_voice": "es-ES-AlvaroNeural",
        "json2video_voice": "es-ES-AlvaroNeural",
        "locale_voices": {
            "es": "es-ES-AlvaroNeural",
            "es-MX": "es-MX-JorgeNeural",
            "es-ES": "es-ES-AlvaroNeural",
            "en": "en-US-GuyNeural",
        },
    },
}