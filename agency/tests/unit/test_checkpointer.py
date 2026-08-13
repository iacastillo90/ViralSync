"""
test_checkpointer.py

Factory de checkpointer para WU-03 (design D2, REQ-PERSIST-04, tasks T-13/T-14):

- `test_build_checkpointer_force_sqlite_returns_memory_saver` — bajo
  FORCE_SQLITE=true (conftest) la factory devuelve un `MemorySaver`: la suite
  SQLite jamás toca Postgres ni exige la dependencia pesada instalada.
- `test_setup_postgres_opens_lifespan_conn_and_async_postgres_saver` — con
  imports mockeados (sys.modules): el lifespan abre una conexión async psycopg
  de larga vida, construye `AsyncPostgresSaver(conn)` y ejecuta `setup(conn)`
  (PERSIST-04-1 — los checkpoints viven en Postgres, no en memoria).
- `test_build_checkpointer_postgres_reuses_lifespan_saver` — tras el setup,
  `build_checkpointer()` en entorno no-SQLite devuelve EL MISMO saver, de modo
  que el graph_app reconstruido en el lifespan usa el checkpointer persistente.
- `test_postgres_swap_discards_memory_without_migration` — PERSIST-04-2
  (non-goal documentado): el swap NO intenta migrar el historial MemorySaver;
  no existe ninguna ruta de migración en el módulo.

Los tests del ramo Postgres inyectan módulos falsos (`psycopg` y
`langgraph.checkpoint.postgres.aio`) en sys.modules vía monkeypatch, porque la
dependencia real no debe ser necesaria para correr la suite SQLite (import lazy
en `backend/db/checkpointer.py`).
"""

import sys
import types

import pytest

import backend.db.checkpointer as checkpointer


def _install_fake_pg(monkeypatch, recorded: dict) -> tuple:
    """Inyecta psycopg + langgraph.checkpoint.postgres.aio falsos en sys.modules.

    El `FakeAsyncConnection.connect` es un classmethod async que registra el
    conninfo recibido; `FakeAsyncPostgresSaver` registra la conn del constructor
    y la conn del `setup(conn=...)`. Devuelve ambas clases.
    """
    class FakeAsyncConnection:
        def __init__(self, conninfo, **kwargs):
            recorded["conninfo"] = conninfo

        async def close(self):
            recorded["closed"] = True

        @classmethod
        async def connect(cls, conninfo, **kwargs):
            return cls(conninfo, **kwargs)

    class FakeAsyncPostgresSaver:
        def __init__(self, conn):
            recorded["saver_conn"] = conn

        async def setup(self):
            recorded["setup_called"] = True

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.AsyncConnection = FakeAsyncConnection
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    fake_postgres_aio = types.ModuleType("langgraph.checkpoint.postgres.aio")
    fake_postgres_aio.AsyncPostgresSaver = FakeAsyncPostgresSaver
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.postgres.aio", fake_postgres_aio)

    return FakeAsyncConnection, FakeAsyncPostgresSaver


def test_build_checkpointer_force_sqlite_returns_memory_saver(monkeypatch):
    """D2/T-13: FORCE_SQLITE=true → MemorySaver; cero contacto con Postgres."""
    monkeypatch.setenv("FORCE_SQLITE", "true")
    from langgraph.checkpoint.memory import MemorySaver

    cp = checkpointer.build_checkpointer()

    assert isinstance(cp, MemorySaver), (
        "bajo FORCE_SQLITE la factory debe devolver MemorySaver, no el saver Postgres"
    )


def test_build_checkpointer_without_sqlite_flag_uses_fallback(monkeypatch):
    """D2/T-14 (comportamiento f59f4bf): sin FORCE_SQLITE y sin setup previo,
    la factory NO crashea — degrada a MemorySaver para que los workers Celery
    (sin lifespan FastAPI) puedan inicializar el grafo sin fallar."""
    monkeypatch.setenv("FORCE_SQLITE", "false")
    # Limpiar cualquier saver residual de otros tests
    import asyncio
    asyncio.run(checkpointer.close_postgres_checkpointer())

    cp = checkpointer.build_checkpointer()
    from langgraph.checkpoint.memory import MemorySaver

    assert isinstance(cp, MemorySaver), (
        "sin setup previo la factory debe degradar a MemorySaver, no crashear"
    )


@pytest.mark.anyio
async def test_setup_postgres_opens_lifespan_conn_and_async_postgres_saver(monkeypatch):
    """PERSIST-04-1 (unit, imports mockeados): setup abre la conn long-lived y
    construye AsyncPostgresSaver(conn) + setup(conn)."""
    recorded: dict = {}
    _, FakeAsyncPostgresSaver = _install_fake_pg(monkeypatch, recorded)

    saver = await checkpointer.setup_postgres_checkpointer()

    assert isinstance(saver, FakeAsyncPostgresSaver)
    assert recorded["conninfo"].startswith("postgresql://"), (
        "el conninfo psycopg NO puede conservar el dialecto asyncpg (+asyncpg)"
    )
    assert "+asyncpg" not in recorded["conninfo"]
    assert recorded["saver_conn"] is not None
    assert recorded["setup_called"] is True, "setup() del saver debe ejecutarse (crea las tablas de checkpoint)"

    await checkpointer.close_postgres_checkpointer()
    assert recorded.get("closed") is True


@pytest.mark.anyio
async def test_build_checkpointer_postgres_reuses_lifespan_saver(monkeypatch):
    """T-13: tras el setup, build_checkpointer() (no-SQLite) devuelve EL MISMO
    saver Postgres — el graph_app reconstruido persiste de verdad."""
    recorded: dict = {}
    _, FakeAsyncPostgresSaver = _install_fake_pg(monkeypatch, recorded)
    monkeypatch.setenv("FORCE_SQLITE", "false")

    saver = await checkpointer.setup_postgres_checkpointer()
    built = checkpointer.build_checkpointer()

    assert isinstance(built, FakeAsyncPostgresSaver)
    assert built is saver, "la factory debe reutilizar el saver del lifespan (misma conn)"

    await checkpointer.close_postgres_checkpointer()


def test_postgres_swap_discards_memory_without_migration():
    """PERSIST-04-2 (non-goal documentado): el swap NO intenta migrar sesiones
    MemorySaver — el módulo sólo decide entre MemorySaver y AsyncPostgresSaver,
    sin ruta de migración ni copia de historial previo."""
    assert not hasattr(checkpointer, "migrate_memory_saver"), (
        "PERSIST-04-2: no debe existir helper de migración de sesiones en memoria"
    )
    assert not hasattr(checkpointer, "migrate_sessions"), (
        "PERSIST-04-2: no debe existir ruta de migración de sesiones"
    )
    # La superficie pública es exactamente la factory + el setup del lifespan
    assert callable(getattr(checkpointer, "build_checkpointer", None))
    assert callable(getattr(checkpointer, "setup_postgres_checkpointer", None))