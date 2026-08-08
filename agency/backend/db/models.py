"""
models.py

Modelos ORM de SQLAlchemy 2.0 Async para la persistencia de datos Enterprise en PostgreSQL.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_type: Mapped[str] = mapped_column(String(64), default="product")
    image_url: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    niche: Mapped[str] = mapped_column(String(128), default="General")
    score_rum: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    gancho_0_5s: Mapped[str] = mapped_column(Text, nullable=False)
    contexto_5_30s: Mapped[str] = mapped_column(Text, nullable=False)
    moraleja_30_50s: Mapped[str] = mapped_column(Text, nullable=False)
    cta_50_60s: Mapped[str] = mapped_column(Text, nullable=False)
    keyword: Mapped[str] = mapped_column(String(64), default="SOLICITUD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id"), nullable=False)
    video_url: Mapped[str] = mapped_column(String(512), nullable=False)
    published_post_id: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"

    # Alineada con migrations/001_init_schema.sql (169-182) + 002 (23-26):
    # la migración SQL es la fuente de verdad para el esquema de producción, de
    # modo que el ORM NO debe declarar columnas ausentes del DDL SQL (p. ej.
    # created_at no existe en la tabla leads). create_all sólo crea las tablas que
    # faltan, y sobre las tablas ya existentes (creadas por las migraciones) el
    # ORM debe mapear exactamente las columnas que SELECT/UPDATE tocan.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(64), nullable=False)
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    views: Mapped[int] = mapped_column(Integer, default=0)
    followers_at_posting: Mapped[int] = mapped_column(Integer, default=0)
    leads_generated: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[Optional[float]] = mapped_column(Float)
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(32), default="VERDE")
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LLMUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
