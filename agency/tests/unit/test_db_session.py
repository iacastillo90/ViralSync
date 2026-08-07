"""test_db_session.py

Unit tests for the async SQLAlchemy session with FORCE_SQLITE.

Proves decision D4 (design.md): with an in-memory SQLite URL the engine uses
a StaticPool so that `init_db()` (create_all) and later `select()` queries
from a NEW session share the SAME in-memory database. A fresh in-memory DB
per connection would otherwise leave every lookup with an empty schema.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from backend.db.session import TARGET_DB_URL, AsyncSessionLocal, init_db
from backend.db.models import Tenant


@pytest.mark.anyio
async def test_target_db_url_is_sqlite_in_memory_when_forced():
    # conftest sets FORCE_SQLITE=true at import time → engine eager-defaults to sqlite.
    assert "sqlite" in TARGET_DB_URL
    assert ":memory:" in TARGET_DB_URL


@pytest.mark.anyio
async def test_engine_explicitly_uses_static_pool_for_in_memory():
    """Design D4: in-memory URL MUST be pinned to StaticPool explicitly, so a
    fresh :memory: DB is not created per connection (shared schema)."""
    from backend.db.session import async_engine
    assert isinstance(async_engine.pool, StaticPool)


@pytest.mark.anyio
async def test_init_db_schema_is_visible_from_a_new_session():
    """init_db() runs create_all once; a NEW session (a different connection
    in the shared StaticPool) still sees the tables — proving the in-memory DB
    is shared, not duplicated per connection."""
    # create_all is idempotent; run twice to prove re-init does not error.
    await init_db()
    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result.all()}
    assert "tenants" in tables
    assert "leads" in tables

    # A real write via one session is visible via another (shared pool).
    from sqlalchemy import select
    async with AsyncSessionLocal() as s1:
        s1.add(Tenant(id="t-shared-1", name="Shared Client"))
        await s1.commit()
    async with AsyncSessionLocal() as s2:
        rows = (await s2.execute(select(Tenant).where(Tenant.id == "t-shared-1"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Shared Client"