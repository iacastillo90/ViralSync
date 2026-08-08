-- agency/migrations/002_add_video_metrics_and_fix_leads.sql
-- Migración SQL 002: Creación de la tabla video_metrics y extensión de columnas en la tabla leads.

-- 1. Tabla de Métricas de Video (Time-series / Snapshots a las 72h)
CREATE TABLE IF NOT EXISTS video_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id            UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    views_72h           BIGINT NOT NULL DEFAULT 0,
    likes               BIGINT DEFAULT 0,
    comments            BIGINT DEFAULT 0,
    shares              BIGINT DEFAULT 0,
    ratio_relativo      NUMERIC(6, 3) NOT NULL DEFAULT 1.000,
    classification      TEXT NOT NULL CHECK (classification IN ('ROJO', 'AMARILLO', 'VERDE')),
    action_taken        TEXT,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_video_metrics_tenant_video ON video_metrics (tenant_id, video_id);
CREATE INDEX IF NOT EXISTS idx_video_metrics_classification ON video_metrics (tenant_id, classification);

-- 2. Extensión de la tabla leads
-- status: el ORM (backend/db/models.py Lead) lo declara y el takeover lo actualiza
-- (handled_by_human). Sin esta columna, cualquier SELECT/UPDATE del modelo Lead
-- falla con UndefinedColumn sobre el esquema de migración.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'new',
    ADD COLUMN IF NOT EXISTS operator_id TEXT,
    ADD COLUMN IF NOT EXISTS conversacion_history JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
