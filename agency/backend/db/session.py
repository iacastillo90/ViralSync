"""
session.py

Configuración del motor asíncrono SQLAlchemy y la gestión de sesiones PostgreSQL con asyncpg.
Incluye validación fail-fast de credenciales en entornos de producción/staging.
"""

import os
import asyncio
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from backend.db.models import Base

logger = logging.getLogger(__name__)

AGENCY_ENV = os.getenv("AGENCY_ENV", "dev").lower()
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "viralsync_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Retry de init_db(): tolera un blip transitorio de Postgres en el primer boot
# (ej. el servidor todavía está arrancando schema) en lugar de matar a uvicorn.
DB_INIT_MAX_ATTEMPTS = int(os.getenv("DB_INIT_MAX_ATTEMPTS", "5"))
DB_INIT_BACKOFF_SECONDS = float(os.getenv("DB_INIT_BACKOFF_SECONDS", "2"))

# Validación de seguridad: Fail-fast ante contraseña por defecto en producción
if AGENCY_ENV in ["prod", "production", "staging"] and POSTGRES_PASSWORD == "postgres":
    raise ValueError("SEGURIDAD: La contraseña de PostgreSQL 'postgres' por defecto está prohibida en entornos staging/prod.")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Normalizar URL: si viene como postgresql:// (psycopg2 style) convertirla a asyncpg
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

SQLITE_FALLBACK_URL = "sqlite+aiosqlite:///:memory:"

# Usar PostgreSQL siempre que el entorno tenga la URL correcta.
# SQLite solo si se fuerza explícitamente con FORCE_SQLITE=true (para tests unitarios rápidos).
TARGET_DB_URL = SQLITE_FALLBACK_URL if os.getenv("FORCE_SQLITE", "false").lower() in ["true", "1"] else DATABASE_URL

logger.info(f"[DB] Usando motor: {'SQLite (test)' if 'sqlite' in TARGET_DB_URL else 'PostgreSQL'} | ENV={AGENCY_ENV}")

engine_kwargs: dict = {"echo": AGENCY_ENV == "dev"}
if "sqlite" not in TARGET_DB_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })
else:
    # SQLite en memoria (:memory:) crea UNA DB nueva por conexión. StaticPool
    # mantiene una única conexión compartida para que init_db() (create_all) y
    # los SELECT posteriores operen sobre el mismo esquema.
    engine_kwargs.update({"poolclass": StaticPool})

async_engine = create_async_engine(TARGET_DB_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Inicializa la base de datos creando las tablas registradas en la metadata.

    Resiliente a un blip transitorio de Postgres al arrancar (create_all contra un
    cluster/healtcheck aún no listo): reintenta hasta DB_INIT_MAX_ATTEMPTS con
    backoff de DB_INIT_BACKOFF_SECONDS. Si se agotan los intentos, re-lanza para
    que el fallo sea visible en logs en lugar de silencioso.
    """
    last_exc: Exception | None = None
    for attempt in range(1, DB_INIT_MAX_ATTEMPTS + 1):
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as exc:  # noqa: BLE001 - error transitorio manejado por retry
            last_exc = exc
            if attempt < DB_INIT_MAX_ATTEMPTS:
                logger.warning(
                    "[DB] init_db() intento %s/%s falló (%s); reintentando en %.1fs",
                    attempt, DB_INIT_MAX_ATTEMPTS, exc, DB_INIT_BACKOFF_SECONDS,
                )
                await asyncio.sleep(DB_INIT_BACKOFF_SECONDS)
            else:
                logger.error(
                    "[DB] init_db() agotó %s intentos creando el esquema: %s",
                    DB_INIT_MAX_ATTEMPTS, exc,
                )
    if last_exc is not None:
        raise last_exc


async def set_tenant_session_context(session: AsyncSession, tenant_id: str) -> None:
    """Configura la variable de sesión app.current_tenant_id para aplicar Row Level Security (RLS)."""
    if "sqlite" not in TARGET_DB_URL:
        from sqlalchemy import text
        await session.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI para inyectar la sesión asíncrona de base de datos."""
    async with AsyncSessionLocal() as session:
        yield session

