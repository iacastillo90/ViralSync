-- agency/migrations/012_voice_personas.sql
-- Migración SQL 012 (S2 — Voice Personas, REQ-VOICE-01): catálogo de personas de voz.
-- Idempotente (patrón IF NOT EXISTS de 002). Aplica sobre el schema previo:
--   - Tabla voice_personas (catálogo con voz por motor + locale_voices JSONB)
--   - scripts.voice_persona_id (FK a voice_personas, REQ-VOICE-04)
--   - Seed de las 3 personas confirmadas por el usuario (proposal "Resolved Decisions #2",
--     design 012) con ON CONFLICT (name) DO NOTHING para re-ejecución segura.
-- locale_voices mapea el idioma destino del render (es/es-MX/es-ES/en) a la voz
-- Edge-TTS correspondiente de cada persona (REQ-VOICE-05: voz del idioma destino).

CREATE TABLE IF NOT EXISTS voice_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    edge_tts_voice TEXT NOT NULL,
    json2video_voice TEXT NOT NULL,
    locale_voices JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE scripts ADD COLUMN IF NOT EXISTS voice_persona_id UUID REFERENCES voice_personas(id);

INSERT INTO voice_personas (name, description, edge_tts_voice, json2video_voice, locale_voices, is_active) VALUES
    ('Masculina Enérgica', 'Voz masculina enérgica para ganchos de alto impacto (es-MX).', 'es-MX-JorgeNeural', 'es-MX-JorgeNeural',
     '{"es": "es-MX-JorgeNeural", "es-MX": "es-MX-JorgeNeural", "es-ES": "es-ES-AlvaroNeural", "en": "en-US-ChristopherNeural"}'::jsonb, TRUE),
    ('Femenina Corporativa', 'Voz femenina corporativa, clara y profesional (es-MX).', 'es-MX-DaliaNeural', 'es-MX-DaliaNeural',
     '{"es": "es-MX-DaliaNeural", "es-MX": "es-MX-DaliaNeural", "es-ES": "es-ES-ElviraNeural", "en": "en-US-JennyNeural"}'::jsonb, TRUE),
    ('Fundador Tech', 'Voz masculina de fundador tech, cercana y aspiracional (es-ES).', 'es-ES-AlvaroNeural', 'es-ES-AlvaroNeural',
     '{"es": "es-ES-AlvaroNeural", "es-MX": "es-MX-JorgeNeural", "es-ES": "es-ES-AlvaroNeural", "en": "en-US-GuyNeural"}'::jsonb, TRUE)
ON CONFLICT (name) DO NOTHING;