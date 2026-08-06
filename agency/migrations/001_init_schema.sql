-- agency/migrations/001_init_schema.sql
-- Modelo de datos relacional multi-tenant para ViralSync.
-- Aislamiento garantizado mediante tenant_id y UUIDs en todas las tablas de negocio.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- --------------------------------------------------------------------- --
-- 1. Tenants (Clientes SaaS de la Agencia)
-- --------------------------------------------------------------------- --
CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    niche               TEXT NOT NULL,
    instagram_business_account_id  TEXT,
    instagram_graph_api_token_ref  TEXT,  -- Referencia a secret manager, nunca token en claro
    litellm_virtual_key TEXT,             -- Virtual key generada en onboarding
    monthly_llm_budget_usd NUMERIC(10, 2) NOT NULL DEFAULT 20.00,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------- --
-- 2. Nichos (Definición de Subdominio & PPP por Tenant)
-- --------------------------------------------------------------------- --
CREATE TABLE niches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    micronicho          TEXT NOT NULL,
    ppp                 TEXT NOT NULL,    -- Promesa Principal de Producto
    personaje_marca_json JSONB NOT NULL DEFAULT '{}',  -- 3 atributos, elementos visuales, objeto
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_niches_tenant ON niches (tenant_id);

-- --------------------------------------------------------------------- --
-- 3. Mapa de Mercado (AGENTS.md 7.7) — Persistente por Nicho & Tenant
-- --------------------------------------------------------------------- --
CREATE TABLE market_maps (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    niche_id         UUID REFERENCES niches(id) ON DELETE CASCADE,
    niche            TEXT NOT NULL,
    errores          JSONB NOT NULL DEFAULT '[]',
    deseos           JSONB NOT NULL DEFAULT '[]',
    objeciones       JSONB NOT NULL DEFAULT '[]',
    creencias_falsas JSONB NOT NULL DEFAULT '[]',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, niche)
);

CREATE INDEX idx_market_maps_tenant_niche ON market_maps (tenant_id, niche);

-- --------------------------------------------------------------------- --
-- 4. Umbrales RUM Dinámicos por Nicho (AGENTS.md 7.1)
-- --------------------------------------------------------------------- --
CREATE TABLE rum_thresholds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    niche       TEXT NOT NULL,
    threshold   NUMERIC(4, 3) NOT NULL,   -- Percentil calculado sobre histórico RUM del nicho
    percentile  NUMERIC(4, 3) NOT NULL,   -- ej. 0.700 = percentil 70
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rum_thresholds_tenant_niche ON rum_thresholds (tenant_id, niche, computed_at DESC);

-- --------------------------------------------------------------------- --
-- 5. Ideas (Candidatas Generadas con Scoring RUM y Filtro 5/50)
-- --------------------------------------------------------------------- --
CREATE TABLE ideas (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    niche_id               UUID REFERENCES niches(id) ON DELETE SET NULL,
    texto                  TEXT NOT NULL,
    gancho                 TEXT,

    -- Filtro 5/50 (AGENTS.md 7.2)
    entendible_nino_5_anos BOOLEAN,
    interesa_50_de_100     BOOLEAN,

    -- Componentes RUM (AGENTS.md 7.1)
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

    -- Clasificación post-publicación (AGENTS.md 7.8)
    origen_reintento_de UUID REFERENCES ideas(id),  -- Si nace de una idea Amarilla/Verde previa

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ideas_tenant_status ON ideas (tenant_id, approval_status);

-- --------------------------------------------------------------------- --
-- 6. Guiones (AGENTS.md 7.4) — 4 Bloques Estructurados
-- --------------------------------------------------------------------- --
CREATE TABLE scripts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idea_id         UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    gancho_0_5s     TEXT NOT NULL,
    contexto_5_30s  TEXT NOT NULL,
    moraleja_30_50s TEXT NOT NULL,
    cta_50_60s      TEXT NOT NULL,
    keyword         TEXT NOT NULL,  -- Palabra clave única del CTA
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scripts_tenant_idea ON scripts (tenant_id, idea_id);

-- --------------------------------------------------------------------- --
-- 7. Videos (Crudo ➔ Editado ➔ Publicado ➔ Métricas 72h)
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

    -- Métricas capturadas a las 72h
    views_72h            BIGINT,
    followers_at_publish  BIGINT,  -- Necesario para el ratio relativo
    classification        TEXT
        CHECK (classification IN ('rojo', 'amarillo', 'verde')),
    metrics_captured_at    TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_videos_tenant_classification ON videos (tenant_id, classification);

-- --------------------------------------------------------------------- --
-- 8. Campañas (Atribución Keyword ➔ Video Publicado)
-- --------------------------------------------------------------------- --
CREATE TABLE campaigns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id    UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    keyword     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'closed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, keyword, status)
);

CREATE INDEX idx_campaigns_active_keyword ON campaigns (tenant_id, keyword) WHERE status = 'active';

-- --------------------------------------------------------------------- --
-- 9. Leads (Captura Inbound en Tiempo Real Vía Webhook Meta)
-- --------------------------------------------------------------------- --
CREATE TABLE leads (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    video_id            UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    keyword             TEXT NOT NULL,
    ig_user_id          TEXT NOT NULL,       -- ID de Instagram de quien escribió
    mensaje_original    TEXT NOT NULL,
    origen              TEXT NOT NULL CHECK (origen IN ('comment', 'dm')),
    calificado_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Toma de control por operador humano desde el dashboard
    handled_by_human_at TIMESTAMPTZ,
    outcome              TEXT CHECK (outcome IN ('convertido', 'descartado', 'sin_respuesta'))
);

CREATE INDEX idx_leads_tenant_video ON leads (tenant_id, video_id);
CREATE INDEX idx_leads_calificado_at ON leads (calificado_at DESC);

-- --------------------------------------------------------------------- --
-- 10. Auditoría de Gasto LLM por Tenant (LiteLLM Budgeting)
-- --------------------------------------------------------------------- --
CREATE TABLE llm_usage_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_name   TEXT NOT NULL,          -- ideation, scriptwriting, etc.
    model_used  TEXT NOT NULL,          -- Cuál del pool respondió (o el fallback pagado)
    was_paid_fallback BOOLEAN NOT NULL DEFAULT false,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    cost_usd    NUMERIC(10, 6) DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_usage_tenant_month ON llm_usage_log (tenant_id, created_at);
