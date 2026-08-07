"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-08-07 10:00:00.000000

El schema real fue aplicado con psql directamente en Postgres desde los archivos
agency/migrations/001_init_schema.sql y 002_add_video_metrics_and_fix_leads.sql.

Esta revisión existe como marcador Alembic del estado inicial —  NO re-crea tablas.
Para nuevas columnas o tablas, crear una revisión 002 en adelante.
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Las tablas ya existen en Postgres (aplicadas vía psql desde migrations/).
    # Alembic no debe re-crearlas. Este upgrade es idempotente: no hace nada.
    # Si el entorno es nuevo, el DBA debe ejecutar:
    #   psql -U agency -d agency -f migrations/001_init_schema.sql
    #   psql -U agency -d agency -f migrations/002_add_video_metrics_and_fix_leads.sql
    pass


def downgrade() -> None:
    # Destruye TODO el schema en orden inverso de dependencias.
    # USAR SOLO EN DEV. En producción requiere aprobación explícita.
    op.execute("""
        DROP TABLE IF EXISTS video_metrics, llm_usage_log, leads, campaigns,
            videos, scripts, ideas, rum_thresholds, market_maps, niches, tenants CASCADE;
        DROP EXTENSION IF EXISTS pgcrypto;
    """)
