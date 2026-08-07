"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-08-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    if "tenants" not in tables:
        with open("migrations/01_init.sql", "r") as f:
            sql = f.read()
        op.execute(sql)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs, llm_usage_logs, video_metrics, leads, posts, scripts, ideas, products, tenants CASCADE;")
