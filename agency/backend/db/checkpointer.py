"""
checkpointer.py

Factory del checkpointer del grafo (design D2, T-14): bajo FORCE_SQLITE=true
(tests/conftest) devuelve un `MemorySaver` — la suite SQLite jamás toca
Postgres ni exige la dependencia pesada instalada (import lazy). En cualquier
otro entorno devuelve un `AsyncPostgresSaver` (langgraph-checkpoint-postgres)
construido sobre una conexión asíncrona psycopg de LARGA VIDA que abre el
lifespan de main.py: los checkpoints viven en PostgreSQL y el grafo
`thread_id=tenant_id` sobrevive al restart del backend (REQ-PERSIST-04-1).

PERSIST-04-2 (non-goal documentado): el swap descarta el historial MemorySaver;
NO existe ruta de migración de sesiones previas — deliberadamente no hay helpers
de migración en este módulo.

Contracto de uso (T-14):
    # lifespan de main.py, entorno Postgres
    await setup_postgres_checkpointer()   # abre conn + setup(conn) + crea tablas
    rebuild_graph_app()                   # graph_execution: grafo con el saver PG

    # shutdown
    await close_postgres_checkpointer()
"""

import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def is_force_sqlite() -> bool:
    """True cuando FORCE_SQLITE=true (tests/conftest.py): la factory → MemorySaver.

    Se evalúa en call-time (no en el import) para respetar el orden de conftest:
    `os.environ["FORCE_SQLITE"] = "true"` se fija ANTES de importar el backend.
    """
    return os.getenv("FORCE_SQLITE", "false").lower() in ("true", "1")


def build_checkpointer() -> Any:
    """Factory del checkpointer activo (D2/T-13):

    - `FORCE_SQLITE=true` → `MemorySaver` (tests unitarios, PERSIST-04-2).
    - resto → el `AsyncPostgresSaver` que el lifespan inicializó con
      `setup_postgres_checkpointer()`; si el lifespan aún no corrió, falla con
      un error claro en lugar de degradar silenciosamente a memoria.
    """
    if is_force_sqlite():
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    if _pg_saver is None:
        raise RuntimeError(
            "Checkpointer Postgres no inicializado: el lifespan debe ejecutar "
            "setup_postgres_checkpointer() antes de servir requests (D2/T-14)."
        )
    return _pg_saver


# Conexión async psycopg de larga vida + saver Postgres, gestionados por el
# lifespan de main.py (setup → rebuild del graph_app → close en shutdown).
_pg_conn: Optional[Any] = None
_pg_saver: Optional[Any] = None


def _psycopg_conninfo() -> str:
    """Traduce `DATABASE_URL` del dialecto asyncpg a un conninfo psycopg válido.

    El engine SQLAlchemy usa `postgresql+asyncpg://…` (session.py), que psycopg
    (langgraph-checkpoint-postgres) no acepta: hay que quitar el sufijo
    `+asyncpg`. Espeja la normalización que ya hace backend/db/session.py:40-41.
    """
    from backend.db.session import DATABASE_URL

    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def setup_postgres_checkpointer() -> Any:
    """Abre la conexión long-lived y devuelve el AsyncPostgresSaver listo.

    Import lazy de psycopg + langgraph.checkpoint.postgres.aio (los tests
    SQLite los inyectan falsos vía sys.modules / nunca los importan). Crea las
    tablas de checkpoint con `setup(conn)` sobre la misma conexión (PERSIST-04-1).
    """
    global _pg_conn, _pg_saver

    from psycopg import AsyncConnection
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    _pg_conn = await AsyncConnection.connect(_psycopg_conninfo(), autocommit=True)
    _pg_saver = AsyncPostgresSaver(_pg_conn)
    await _pg_saver.setup()
    logger.info("[checkpointer] AsyncPostgresSaver inicializado sobre PostgreSQL")
    return _pg_saver


async def close_postgres_checkpointer() -> None:
    """Cierra la conexión long-lived y resetea el saver (shutdown del lifespan)."""
    global _pg_conn, _pg_saver

    if _pg_conn is not None:
        try:
            await _pg_conn.close()
        except Exception as exc:  # noqa: BLE001 - cierre best-effort en shutdown
            logger.warning("[checkpointer] error cerrando conexión: %s", exc)
    _pg_conn = None
    _pg_saver = None