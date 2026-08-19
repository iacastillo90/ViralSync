-- agency/migrations/013_videos_platform.sql
-- Migración SQL 013 (S3 — Auto-Publicación, REQ-PUB-01/05): plataforma destino
-- por video y mejor slot de publicación por tenant.
-- Idempotente (patrón IF NOT EXISTS de 002). Aplica sobre el schema previo:
--   - videos.platform   TEXT NOT NULL DEFAULT 'instagram'   (REQ-PUB-01)
--   - tenants.best_time_slot JSONB                          (REQ-PUB-05;
--     {"day_of_week": 2, "hour": 19, "source": "gemini"|"heuristic"})
--   - CHECK de publish_approval_status ampliado: el write-back del auto-publish
--     (REQ-PUB-04) persiste 'published'; el CHECK de 001 sólo admitía
--     pending|approved|rejected. Drop+ADD idempotente por nombre canónico
--     PG <tabla>_<columna>_check.

ALTER TABLE videos ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'instagram';

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS best_time_slot JSONB;

ALTER TABLE videos DROP CONSTRAINT IF EXISTS videos_publish_approval_status_check;
ALTER TABLE videos ADD CONSTRAINT videos_publish_approval_status_check
    CHECK (publish_approval_status IN ('pending', 'approved', 'rejected', 'published'));