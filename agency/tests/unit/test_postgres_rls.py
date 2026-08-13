"""
test_postgres_rls.py

Pruebas unitarias para verificar el helper RLS y la migración SQL 006_enable_rls.sql (REQ-RLS-01/02).
"""

import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.db.session import set_tenant_session_context


@pytest.mark.anyio
async def test_set_tenant_session_context_executes_set_local():
    """Verifica que set_tenant_session_context ejecute la sentencia SET LOCAL en PostgreSQL."""
    mock_session = AsyncMock()
    
    # En SQLite de test se ignora, pero en PG ejecuta el SET LOCAL
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("backend.db.session.TARGET_DB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agency")
        await set_tenant_session_context(mock_session, "tenant_test_rls")
        
    mock_session.execute.assert_called_once()
    sql_call = str(mock_session.execute.call_args[0][0])
    assert "SET LOCAL app.current_tenant_id" in sql_call


def test_migration_006_file_exists():
    """Verifica que el archivo de migración 006_enable_rls.sql exista y contenga RLS."""
    repo_root = Path(__file__).resolve().parents[2]  # .../agency (tests/unit → tests)
    migration_path = repo_root / "migrations" / "006_enable_rls.sql"
    assert migration_path.exists()
    
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "ENABLE ROW LEVEL SECURITY" in content
    assert "CREATE POLICY" in content
    assert "app.current_tenant_id" in content
