-- agency/migrations/011_leads_qualification.sql
-- Migración SQL 011 (S1 — DM Leads CRM, REQ-DM-LEAD-02): calificación de leads.
-- Idempotente (patrón IF NOT EXISTS de 002). Aplica sobre el schema previo:
--   - leads.qualification_score INTEGER NOT NULL DEFAULT 0 (score 0-100 del scoring)
--   - leads.platform TEXT NOT NULL DEFAULT 'instagram' (origen del lead)
--   - leads.dedup_hash TEXT (sha256(ig_user_id|mensaje) para idempotencia del webhook)
--   - leads.video_id pasa a NULLABLE: el webhook de Meta no siempre trae video y
--     sin DROP NOT NULL el INSERT de un lead de webhook fallaría por FK NOT NULL.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS qualification_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'instagram',
    ADD COLUMN IF NOT EXISTS dedup_hash TEXT,
    ALTER COLUMN video_id DROP NOT NULL;

-- Idempotencia REQ-DM-LEAD-05: un mismo (ig_user_id, mensaje) nunca duplica filas.
CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_dedup_hash ON leads (dedup_hash);
-- Índice para filtrar por estado (REQ-DM-LEAD-02).
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
