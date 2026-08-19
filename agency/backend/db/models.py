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
from typing import Optional, Any
from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, ForeignKey, Uuid, Numeric, Index
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
    # Migración 013 (S3 — Auto-Publicación, REQ-PUB-05): mejor slot de publicación
    # sugerido por Gemini o heurística, persistido como JSONB
    # {"day_of_week": int 0-6, "hour": int 0-23, "source": "gemini"|"heuristic"}.
    best_time_slot: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)



class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("idx_campaigns_tenant", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[Optional[str]] = mapped_column(Text)
    target_reels_count: Mapped[int] = mapped_column(Integer, default=8)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Idea(Base):
    __tablename__ = "ideas"
    __table_args__ = (
        Index("idx_ideas_tenant_approval_created", "tenant_id", "approval_status", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(ForeignKey("campaigns.id"))
    niche_id: Mapped[Optional[str]] = mapped_column(ForeignKey("niches.id"))
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    gancho: Mapped[Optional[str]] = mapped_column(Text)
    # Filtro 5/50
    entendible_nino_5_anos: Mapped[Optional[bool]] = mapped_column(Boolean)
    interesa_50_de_100: Mapped[Optional[bool]] = mapped_column(Boolean)
    # Componentes RUM
    universalidad: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    intensidad: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    claridad: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    shareability: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    distribucion: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    alineacion: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    rum_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 5))
    # rum_thresholds no tiene modelo ORM propio; sin FK declarada el create_all de
    # SQLite (tests) no exige la tabla, y en Postgres la FK real vive en la DDL.
    rum_threshold_id: Mapped[Optional[str]] = mapped_column(Uuid(as_uuid=False))
    passes_threshold: Mapped[Optional[bool]] = mapped_column(Boolean)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    origen_reintento_de: Mapped[Optional[str]] = mapped_column(ForeignKey("ideas.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"
    __table_args__ = (
        Index("idx_scripts_tenant_approval", "tenant_id", "approval_status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    gancho_0_5s: Mapped[str] = mapped_column(Text, nullable=False)
    contexto_5_30s: Mapped[str] = mapped_column(Text, nullable=False)
    moraleja_30_50s: Mapped[str] = mapped_column(Text, nullable=False)
    cta_50_60s: Mapped[str] = mapped_column(Text, nullable=False)
    keyword: Mapped[str] = mapped_column(String(64), default="SOLICITUD")
    # Migración 008: aprobación de guion y scoring de tendencias
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    trend_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    trend_rationale: Mapped[Optional[str]] = mapped_column(Text)
    # Migración 012 (S2 — Voice Personas, REQ-VOICE-04): persona de voz asociada al
    # guion; el render resuelve tts_voice/azure voice desde ella por idioma (REQ-VOICE-05).
    voice_persona_id: Mapped[Optional[str]] = mapped_column(ForeignKey("voice_personas.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoicePersona(Base):
    # Alineada con migrations/012_voice_personas.sql (REQ-VOICE-01): catálogo de
    # personas de voz con voz por motor (Edge-TTS + json2video Azure) y un mapa
    # locale_voices (JSONB) para resolver la voz del idioma destino en el render.
    __tablename__ = "voice_personas"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    edge_tts_voice: Mapped[str] = mapped_column(Text, nullable=False)
    json2video_voice: Mapped[str] = mapped_column(Text, nullable=False)
    locale_voices: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CompetitorAccount(Base):
    # Alineada con migrations/014_competitor_accounts.sql (REQ-COMP-01): catálogo
    # de cuentas competidoras por tenant (S4 — Competitor Benchmark). La ingestión
    # (REQ-COMP-02) indexa hooks con source="competitor" y el benchmark (REQ-COMP-04)
    # excluye las cuentas inactivas vía idx_competitor_accounts_tenant.
    __tablename__ = "competitor_accounts"
    __table_args__ = (
        Index("idx_competitor_accounts_tenant", "tenant_id", "is_active"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="instagram")
    username: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    niche: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Niche(Base):
    # Alineada con migrations/001_init_schema.sql (24-31): micronicho/ppp/
    # personaje_marca_json. La migración SQL es la fuente de verdad — el DDL de
    # niches NO declara una columna "niche" (sólo micronicho), por lo que el ORM
    # mapea exactamente las columnas presentes para no reintroducir el 503 por
    # UndefinedColumn al consultar la persona de marca del tenant.
    __tablename__ = "niches"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    micronicho: Mapped[str] = mapped_column(Text, nullable=False)
    ppp: Mapped[str] = mapped_column(Text, nullable=False)
    personaje_marca_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_tenant_status_calificado", "tenant_id", "status", "calificado_at"),
        # Migración 011 (REQ-DM-LEAD-02): índice para filtrar por estado.
        Index("idx_leads_status", "status"),
    )


    # Alineada con migrations/001_init_schema.sql (169-182) + 002 (23-26) + 011:
    # la migración SQL es la fuente de verdad para el esquema de producción, de
    # modo que el ORM NO debe declarar columnas ausentes del DDL SQL (p. ej.
    # created_at no existe en la tabla leads). create_all sólo crea las tablas que
    # faltan, y sobre las tablas ya existentes (creadas por las migraciones) el
    # ORM debe mapear exactamente las columnas que SELECT/UPDATE tocan.
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    # Migración 011: video_id pasa a nullable — el webhook de Meta no siempre trae video.
    video_id: Mapped[Optional[str]] = mapped_column(Uuid(as_uuid=False))
    keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    ig_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mensaje_original: Mapped[str] = mapped_column(Text, nullable=False)
    origen: Mapped[str] = mapped_column(String(64), nullable=False, default="comment")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    # Migración 011 (REQ-DM-LEAD-02/03): scoring 0-100 + plataforma origen.
    qualification_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="instagram")
    # Migración 011 (REQ-DM-LEAD-05): sha256(ig_user_id|mensaje) para idempotencia del webhook.
    dedup_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    calificado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    handled_by_human_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[Optional[str]] = mapped_column(String(32))
    operator_id: Mapped[Optional[str]] = mapped_column(String(64))
    conversacion_history: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    # Alineada con migrations/005_add_products_object_key.sql (REQ-PERSIST-01/05):
    # la migración SQL es la fuente de verdad — el ORM declara EXACTAMENTE las
    # columnas del DDL 005 (id, tenant_id, name, description, product_image_url,
    # object_key, created_at). `object_key` es la key ESTABLE del objeto en MinIO
    # (D-5): la URL presignada expira; la key no — el graph la re-firma en cada
    # lectura (SH-05-3) o cae a la URL almacenada en filas legacy NULL (SH-05-4).
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    product_image_url: Mapped[Optional[str]] = mapped_column(Text)
    object_key: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        Index("idx_videos_tenant_script_published", "tenant_id", "script_id", "published_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id"), nullable=False)
    raw_video_uri: Mapped[Optional[str]] = mapped_column(Text)
    edited_video_uri: Mapped[Optional[str]] = mapped_column(Text)
    # Motor que generó el render (migración 007): 'json2video' | 'local'.
    provider: Mapped[Optional[str]] = mapped_column(String(20))
    # Migración 013 (S3 — Auto-Publicación, REQ-PUB-01): plataforma destino del
    # video; el auto-publish rutea por ella (REQ-PUB-02).
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="instagram")
    publish_approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    instagram_post_id: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    views_72h: Mapped[Optional[int]] = mapped_column(Integer)
    followers_at_publish: Mapped[Optional[int]] = mapped_column(Integer)
    classification: Mapped[Optional[str]] = mapped_column(String(32))
    metrics_captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ScriptVariant(Base):
    __tablename__ = "script_variants"
    __table_args__ = (
        Index("idx_script_variants_script", "script_id", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    variant_label: Mapped[str] = mapped_column(String(10), default="B")
    gancho_0_5s_variant: Mapped[str] = mapped_column(Text, nullable=False)
    views_72h: Mapped[int] = mapped_column(Integer, default=0)
    conversion_72h: Mapped[int] = mapped_column(Integer, default=0)
    winner: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class VideoMetric(Base):
    __tablename__ = "video_metrics"
    __table_args__ = (
        Index("idx_video_metrics_tenant_captured", "tenant_id", "captured_at"),
    )


    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False, index=True)
    views_72h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    ratio_relativo: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=1.000)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="VERDE")
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    __table_args__ = (
        Index("idx_scheduled_posts_tenant_date", "tenant_id", "scheduled_at", "status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    video_id: Mapped[Optional[str]] = mapped_column(ForeignKey("videos.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="instagram_reels")
    caption: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    post_id: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)