"""test_lifespan.py

Integration test for design D4 / spec requirement "DB init wired and idempotent":
FastAPI app startup must trigger `init_db()`, and re-running init_db is idempotent.
"""

import pytest
from contextlib import asynccontextmanager

import backend.main as main_module
from backend.db.session import init_db


@pytest.mark.anyio
async def test_lifespan_calls_init_db_on_startup(monkeypatch):
    """Entering the app's lifespan MUST call init_db exactly once (once per startup)."""
    calls = []

    async def fake_init_db():
        calls.append(True)

    # Replace init_db in the module namespace that main imports from to observe the call.
    monkeypatch.setattr(main_module, "init_db", fake_init_db)

    lifespan = main_module.lifespan
    async with lifespan(main_module.app):
        assert len(calls) == 1, f"init_db should be called once on startup, got {len(calls)}"


@pytest.mark.anyio
async def test_init_db_running_twice_is_idempotent():
    """Re-running init_db() on an already-initialized DB must not error."""
    await init_db()
    await init_db()