"""Add compound performance indexes for multi-tenant query optimization

Revision ID: 006
Revises: 001
Create Date: 2026-08-11 18:00:00.000000

Crea índices compuestos en Postgres para acelerar filtrado y ordenación multi-tenant:
- idx_ideas_tenant_approval_created: (tenant_id, approval_status, created_at DESC)
- idx_leads_tenant_status_calificado: (tenant_id, status, calificado_at DESC)
- idx_videos_tenant_script_published: (tenant_id, script_id, published_at DESC)
- idx_video_metrics_tenant_captured: (tenant_id, captured_at DESC)
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'idx_ideas_tenant_approval_created',
        'ideas',
        ['tenant_id', 'approval_status', sa.text('created_at DESC')],
        if_not_exists=True,
    )
    op.create_index(
        'idx_leads_tenant_status_calificado',
        'leads',
        ['tenant_id', 'status', sa.text('calificado_at DESC')],
        if_not_exists=True,
    )
    op.create_index(
        'idx_videos_tenant_script_published',
        'videos',
        ['tenant_id', 'script_id', sa.text('published_at DESC')],
        if_not_exists=True,
    )
    op.create_index(
        'idx_video_metrics_tenant_captured',
        'video_metrics',
        ['tenant_id', sa.text('captured_at DESC')],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index('idx_video_metrics_tenant_captured', table_name='video_metrics', if_exists=True)
    op.drop_index('idx_videos_tenant_script_published', table_name='videos', if_exists=True)
    op.drop_index('idx_leads_tenant_status_calificado', table_name='leads', if_exists=True)
    op.drop_index('idx_ideas_tenant_approval_created', table_name='ideas', if_exists=True)
