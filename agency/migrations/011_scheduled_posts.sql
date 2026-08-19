-- =============================================================================
-- Migración 011: Publicaciones Programadas (Auto-Publicador Calendario)
-- =============================================================================

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    platform VARCHAR(32) NOT NULL DEFAULT 'instagram_reels',
    caption TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'published', 'failed', 'cancelled')),
    published_at TIMESTAMP WITH TIME ZONE,
    post_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_tenant_date ON scheduled_posts (tenant_id, scheduled_at, status);
