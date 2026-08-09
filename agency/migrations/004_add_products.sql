-- agency/migrations/004_add_products.sql
-- Migración SQL 004 (ADD-only, REQ-PERSIST-01): Tabla `products` por tenant.
-- La migración SQL es la fuente de verdad del esquema (convención DDL-as-truth):
-- el ORM `backend/db/models.py Product` mapea EXACTAMENTE estas columnas.
-- Montada vía docker-entrypoint-initdb.d (compose `postgres` monta
-- ./migrations:/docker-entrypoint-initdb.d:ro) — sin backfill de datos.
CREATE TABLE IF NOT EXISTS products (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    description       TEXT,
    product_image_url TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_tenant ON products (tenant_id);