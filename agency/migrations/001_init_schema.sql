-- migrations/001_init_schema.sql
--
-- Modelo de datos multi-tenant. Aislamiento por tenant_id en cada tabla
-- de negocio (AGENTS.md sección 1: "cada cliente tiene su propio
-- namespace de datos, su propio presupuesto de LLM y su propio historial
-- de contenido").

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- --------------------------------------------------------------------- --
-- Tenants
-- --------------------------------------------------------------------- --

CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    niche               TEXT NOT NULL,
    instagram_business_account_id  TEXT,
    instagram_graph_api_token_ref  TEXT,  -- referencia a secret manager, nunca el token en claro
    litellm_virtual_key TEXT,             -- generada al onboarding (ver gateway/*.yaml)
    monthly_llm_budget_usd NUMERIC(10, 2) NOT NULL DEFAULT 20.00,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------- --
-- Mapa de mercado (AGENTS.md 7.7) — persistente por nicho de cada tenant
-- --------------------------------------------------------------------- --

CREATE TABLE market_maps (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    niche       TEXT NOT NULL,
    errores     JSONB NOT NULL DEFAULT '[]',
    deseos      JSONB NOT NULL DEFAULT '[]',
    objeciones  JSONB NOT NULL DEFAULT '[]',
    creencias_falsas JSONB NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, niche)
);

-- --------------------------------------------------------------------- --
-- Umbral RUM dinámico por nicho (AGENTS.md 7.1) — versionado, nunca fijo
-- --------------------------------------------------------------------- --

CREATE TABLE rum_thresholds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    niche       TEXT NOT NULL,
    threshold   NUMERIC(4, 3) NOT NULL,   -- percentil calculado sobre histórico RUM del nicho
    percentile  NUMERIC(4, 3) NOT NULL,   -- ej. 0.700 = percentil 70
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rum_thresholds_tenant_niche ON rum_thresholds (tenant_id, niche, computed_at DESC);

-- --------------------------------------------------------------------- --
-- Ideas: candidatas generadas, con scoring RUM y filtro 5/50
-- --------------------------------------------------------------------- --

CREATE TABLE ideas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    texto               TEXT NOT NULL,
    gancho              TEXT,

    -- filtro 5/50 (AGENTS.md 7.2)
    entendible_nino_5_anos BOOLEAN,
    interesa_50_de_100     BOOLEAN,

    -- componentes RUM (AGENTS.md 7.1)
    universalidad   NUMERIC(3, 2),
    intensidad      NUMERIC(3, 2),
    claridad        NUMERIC(3, 2),
    shareability    NUMERIC(3, 2),
    distribucion    NUMERIC(3, 2),
    alineacion      NUMERIC(3, 2),
    rum_score       NUMERIC(6, 5),

    rum_threshold_id UUID REFERENCES rum_thresholds(id),
    passes_threshold BOOLEAN,

    approval_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected')),

    -- clasificación post-publicación (AGENTS.md 7.8) — se llena luego, vía videos
    origen_reintento_de UUID REFERENCES ideas(id),  -- si nace de una idea Amarilla/Verde previa

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ideas_tenant_status ON ideas (tenant_id, approval_status);

-- --------------------------------------------------------------------- --
-- Guiones (AGENTS.md 7.4) — 4 bloques
-- --------------------------------------------------------------------- --

CREATE TABLE scripts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idea_id         UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    gancho_0_5s     TEXT NOT NULL,
    contexto_5_30s  TEXT NOT NULL,
    moraleja_30_50s TEXT NOT NULL,
    cta_50_60s      TEXT NOT NULL,
    keyword         TEXT NOT NULL,  -- palabra clave única del CTA, ver campaigns/leads
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------- --
-- Videos: crudo -> editado -> publicado, con métricas y clasificación
-- --------------------------------------------------------------------- --

CREATE TABLE videos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    script_id           UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,

    raw_video_uri       TEXT,
    edited_video_uri    TEXT,

    publish_approval_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (publish_approval_status IN ('pending', 'approved', 'rejected')),

    instagram_post_id   TEXT,
    published_at        TIMESTAMPTZ,

    -- métricas capturadas a las 72h (loop de la sección 1)
    views_72h            BIGINT,
    followers_at_publish  BIGINT,  -- necesario para el ratio, la clasificación es SIEMPRE relativa
    classification        TEXT
        CHECK (classification IN ('rojo', 'amarillo', 'verde')),
    metrics_captured_at    TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_videos_tenant_classification ON videos (tenant_id, classification);

-- --------------------------------------------------------------------- --
-- Campañas: liga la keyword de un video publicado con su atribución
-- --------------------------------------------------------------------- --

CREATE TABLE campaigns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id    UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    keyword     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'closed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, keyword, status)  -- una keyword activa a la vez por tenant, evita colisiones de atribución
);

CREATE INDEX idx_campaigns_active_keyword ON campaigns (tenant_id, keyword) WHERE status = 'active';

-- --------------------------------------------------------------------- --
-- Leads (AGENTS.md 7.9) — captura inbound en tiempo real vía webhook
-- --------------------------------------------------------------------- --

CREATE TABLE leads (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id            UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    keyword             TEXT NOT NULL,
    ig_user_id          TEXT NOT NULL,       -- id de Instagram de quien comentó/escribió, no el nombre
    mensaje_original    TEXT NOT NULL,
    origen              TEXT NOT NULL CHECK (origen IN ('comment', 'dm')),
    calificado_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- el humano toma la conversación desde el dashboard; el sistema nunca vende
    handled_by_human_at TIMESTAMPTZ,
    outcome              TEXT CHECK (outcome IN ('convertido', 'descartado', 'sin_respuesta'))
);

CREATE INDEX idx_leads_tenant_video ON leads (tenant_id, video_id);
CREATE INDEX idx_leads_calificado_at ON leads (calificado_at DESC);

-- --------------------------------------------------------------------- --
-- Auditoría de gasto por tenant (presupuesto de LLM, AGENTS.md sección 1)
-- --------------------------------------------------------------------- --

CREATE TABLE llm_usage_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_name   TEXT NOT NULL,          -- ideation, scriptwriting, etc.
    model_used  TEXT NOT NULL,          -- cuál del pool respondió (o el fallback pagado)
    was_paid_fallback BOOLEAN NOT NULL DEFAULT false,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    cost_usd    NUMERIC(10, 6) DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_usage_tenant_month ON llm_usage_log (tenant_id, created_at);
