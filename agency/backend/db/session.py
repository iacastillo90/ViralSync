"""
session.py

Configuración del motor asíncrono SQLAlchemy y la gestión de sesiones PostgreSQL con asyncpg.
Incluye validación fail-fast de credenciales en entornos de producción/staging.
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
SQLITE_FALLBACK_URL = "sqlite+aiosqlite:///:memory:"

# Determinar si se usa PostgreSQL o SQLite fallback para desarrollo/pruebas
TARGET_DB_URL = DATABASE_URL if os.getenv("USE_POSTGRES", "False").lower() in ["true", "1"] else SQLITE_FALLBACK_URL

engine_kwargs = {"echo": False}
if "sqlite" not in TARGET_DB_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })

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
