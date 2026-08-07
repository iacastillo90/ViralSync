"""
session.py

Configuración del motor asíncrono SQLAlchemy y la gestión de sesiones PostgreSQL con asyncpg.
Incluye validación fail-fast de credenciales en entornos de producción/staging.
"""

import os
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
    """Inicializa la base de datos creando las tablas registradas en la metadata."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI para inyectar la sesión asíncrona de base de datos."""
    async with AsyncSessionLocal() as session:
        yield session
