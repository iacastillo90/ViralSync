"""
models.py

Modelos ORM de SQLAlchemy 2.0 Async para la persistencia de datos Enterprise en PostgreSQL.

El esquema de producción lo definen las migraciones SQL (migrations/*.sql): los
PK/FK UUID de las tablas de negocio (tenants, ideas, scripts, leads, video_metrics)
NO pueden mapearse como VARCHAR. Vía Uuid(as_uuid=False) el ORM expresa los ids como
str (idioma de todos los seeds/routers) y genera CHAR(32) en SQLite / uuid nativo en
Postgres, de modo que create_all nunca choca con las tablas ya creadas por las
migraciones.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, Uuid, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    niche: Mapped[str] = mapped_column(Text, nullable=False, default="General")
    instagram_business_account_id: Mapped[Optional[str]] = mapped_column(Text)
    instagram_graph_api_token_ref: Mapped[Optional[str]] = mapped_column(Text)
    litellm_virtual_key: Mapped[Optional[str]] = mapped_column(Text)
    monthly_llm_budget_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=20.0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)



class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    niche: Mapped[str] = mapped_column(String(128), default="General")
    score_rum: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    gancho_0_5s: Mapped[str] = mapped_column(Text, nullable=False)
    contexto_5_30s: Mapped[str] = mapped_column(Text, nullable=False)
    moraleja_30_50s: Mapped[str] = mapped_column(Text, nullable=False)
    cta_50_60s: Mapped[str] = mapped_column(Text, nullable=False)
    keyword: Mapped[str] = mapped_column(String(64), default="SOLICITUD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"

    # Alineada con migrations/001_init_schema.sql (169-182) + 002 (23-26):
    # la migración SQL es la fuente de verdad para el esquema de producción, de
    # modo que el ORM NO debe declarar columnas ausentes del DDL SQL (p. ej.
    # created_at no existe en la tabla leads). create_all sólo crea las tablas que
    # faltan, y sobre las tablas ya existentes (creadas por las migraciones) el
    # ORM debe mapear exactamente las columnas que SELECT/UPDATE tocan.
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    ig_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mensaje_original: Mapped[str] = mapped_column(Text, nullable=False)
    origen: Mapped[str] = mapped_column(String(64), nullable=False, default="comment")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    calificado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    handled_by_human_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[Optional[str]] = mapped_column(String(32))
    operator_id: Mapped[Optional[str]] = mapped_column(String(64))
    conversacion_history: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoMetric(Base):
    """Métricas de rendimiento de video por tenant en ventana de 72 horas."""
    __tablename__ = "video_metrics"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    views: Mapped[int] = mapped_column(Integer, default=0)
    followers_at_posting: Mapped[int] = mapped_column(Integer, default=0)
    leads_generated: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[Optional[float]] = mapped_column(Float)
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(32), default="VERDE")
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)