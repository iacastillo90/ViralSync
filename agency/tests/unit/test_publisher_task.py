"""
test_publisher_task.py

S3 — Auto-Publicación (REQ-PUB-02/04/07): el worker
`auto_publish_scheduled_videos_task` delega al microservicio publisher (:8002)
con el contrato de `agents/nodes/publish.py`: credenciales tenant-first,
routing por `video.platform` e idempotencia por `publish_approval_status`
(tras publicar, el video queda 'published' y deja de matchear la query).
"""

import asyncio
import hashlib
import uuid as uuid_mod
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy import select

from backend.db.session import init_db, AsyncSessionLocal
from workers.publisher_task import auto_publish_scheduled_videos_task, _build_credentials

PUBLISHED_POST_ID = "ig_post_test_123"


# ---------------------------------------------------------------------------
# Helpers de seed (patrón test_auto_publisher: AsyncSessionLocal sobre el SQLite
# compartido de StaticPool; el worker abre su propia sesión y ve las filas).
# ---------------------------------------------------------------------------

def _seed_tenant(tenant_id, token_ref=None, account_id=None):
    """Inserta un tenant en la DB compartida (idempotente por PK)."""
    from backend.db.models import Tenant

    async def _run():
        async with AsyncSessionLocal() as session:
            existing = (
                await session.execute(select(Tenant).where(Tenant.id == tenant_id))
            ).scalars().first()
            if existing:
                existing.instagram_graph_api_token_ref = token_ref
                existing.instagram_business_account_id = account_id
                await session.commit()
                return existing
            tenant = Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                instagram_business_account_id=account_id,
                instagram_graph_api_token_ref=token_ref,
            )
            session.add(tenant)
            await session.commit()
            return tenant

    return asyncio.run(_run())


def _new_tenant_id():
    """Tenant id con forma UUID (columna Uuid(as_uuid=False) del ORM)."""
    return str(uuid_mod.uuid4())


def _seed_video(tenant_id, *, platform="instagram", status="approved", published_at=None):
    """Inserta un video (con script+idea mínimos) para el auto-publish."""
    from backend.db.models import Video, Script, Idea

    async def _run():
        async with AsyncSessionLocal() as session:
            idea = Idea(id=str(uuid_mod.uuid4()), tenant_id=tenant_id, texto="Idea test de auto-publish")
            session.add(idea)
            await session.flush()
            script = Script(
                id=str(uuid_mod.uuid4()),
                tenant_id=tenant_id,
                idea_id=idea.id,
                gancho_0_5s="Gancho",
                contexto_5_30s="Contexto",
                moraleja_30_50s="Moraleja",
                cta_50_60s="CTA",
            )
            session.add(script)
            await session.flush()
            video = Video(
                id=str(uuid_mod.uuid4()),
                tenant_id=tenant_id,
                script_id=script.id,
                edited_video_uri=f"http://minio:9000/{tenant_id}/final.mp4",
                platform=platform,
                publish_approval_status=status,
                published_at=published_at,
            )
            session.add(video)
            await session.commit()
            return video

    return asyncio.run(_run())


def _load_video(video_id):
    """Recarga la fila `videos` tras el write-back del worker."""
    from backend.db.models import Video

    async def _run():
        async with AsyncSessionLocal() as session:
            return (
                await session.execute(select(Video).where(Video.id == video_id))
            ).scalars().first()

    return asyncio.run(_run())


class _FakeAsyncClient:
    """Cliente httpx fake: registra cada POST y devuelve la respuesta del micro."""

    def __init__(self, *args, **kwargs):
        self.posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None, **kwargs):
        self.posts.append((url, json))
        return _FakePublishResponse()


class _FakePublishResponse:
    status_code = 201

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "status": "published",
            "published_post_id": PUBLISHED_POST_ID,
            "tenant_id": "any",
            "platform": "instagram",
        }


# ---------------------------------------------------------------------------
# REQ-PUB-02 — la factory rutea por platform
# ---------------------------------------------------------------------------

def test_factory_routes_by_platform():
    from microservices.publisher.adapters import (
        PublisherFactory,
        InstagramGraphPublisher,
        TikTokPublisher,
        YouTubeShortsPublisher,
    )

    assert isinstance(PublisherFactory.get_publisher("tiktok"), TikTokPublisher)
    assert isinstance(PublisherFactory.get_publisher("youtube_shorts"), YouTubeShortsPublisher)
    assert isinstance(PublisherFactory.get_publisher("instagram"), InstagramGraphPublisher)
    # Legado del calendario (instagram_reels) cae al adaptador Instagram.
    assert isinstance(PublisherFactory.get_publisher("instagram_reels"), InstagramGraphPublisher)


# ---------------------------------------------------------------------------
# REQ-PUB-07 — credenciales tenant-first con fallback a env
# ---------------------------------------------------------------------------

def test_build_credentials_tenant_first(monkeypatch):
    asyncio.run(init_db())
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "env_account_123")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_token_456")

    with_tokens = _seed_tenant(_new_tenant_id(), token_ref="token_tenant", account_id="ig_tenant")
    user_id, token = _build_credentials(with_tokens)
    assert user_id == "ig_tenant", "El tenant con token debe usarlo (no el env)"
    assert token == "token_tenant"

    without_tokens = _seed_tenant(_new_tenant_id())
    user_id, token = _build_credentials(without_tokens)
    assert user_id == "env_account_123", "Tenant sin token cae al env"
    assert token == "env_token_456"


# ---------------------------------------------------------------------------
# REQ-PUB-04 — publica videos approved vencidos y persiste el write-back
# ---------------------------------------------------------------------------

def test_auto_publish_publishes_approved_due_video_and_persists():
    asyncio.run(init_db())
    tenant_id = _new_tenant_id()
    _seed_tenant(tenant_id, token_ref="token_tenant", account_id="ig_tenant")
    # REQ-PUB-04: video 'approved' + platform instagram + SIN published_at
    video = _seed_video(tenant_id, published_at=None)

    fake = _FakeAsyncClient()
    with patch("workers.publisher_task.httpx.AsyncClient", lambda *a, **k: fake):
        res = auto_publish_scheduled_videos_task()

    assert res["status"] == "COMPLETED"
    # El worker es global por diseño (publica todos los videos vencidos de la DB
    # compartida); este test verifica SU video, no conteos globales del suite.
    my_posts = [p for p in fake.posts if p[1]["tenant_id"] == tenant_id]
    assert len(my_posts) == 1, "El video del tenant debe publicarse exactamente una vez"

    url, payload = my_posts[0]
    assert url.endswith("/publish"), "El worker debe delegar al microservicio :8002/publish"
    assert payload["tenant_id"] == tenant_id
    assert payload["video_url"] == video.edited_video_uri
    assert payload["platform"] == "instagram"
    assert payload["instagram_user_id"] == "ig_tenant"
    assert payload["access_token"] == "token_tenant"
    # Contrato de idempotencia (RESILIENCE-001): sha256(tenant|platform|uri)
    expected_key = hashlib.sha256(
        f"{tenant_id}|instagram|{video.edited_video_uri}".encode("utf-8")
    ).hexdigest()
    assert payload["idempotency_key"] == expected_key

    row = _load_video(video.id)
    assert row.publish_approval_status == "published"
    assert row.instagram_post_id == PUBLISHED_POST_ID
    assert row.published_at is not None


def test_reexecution_does_not_republish():
    asyncio.run(init_db())
    tenant_id = _new_tenant_id()
    _seed_tenant(tenant_id)
    due = datetime.now(timezone.utc) - timedelta(hours=2)
    video = _seed_video(tenant_id, published_at=due)

    fake = _FakeAsyncClient()
    with patch("workers.publisher_task.httpx.AsyncClient", lambda *a, **k: fake):
        auto_publish_scheduled_videos_task()
        auto_publish_scheduled_videos_task()

    my_posts = [p for p in fake.posts if p[1]["tenant_id"] == tenant_id]
    assert len(my_posts) == 1, "La re-ejecución no debe volver a publicar un video ya 'published'"

    row = _load_video(video.id)
    assert row.publish_approval_status == "published"


def test_video_pending_is_not_published():
    asyncio.run(init_db())
    tenant_id = _new_tenant_id()
    _seed_tenant(tenant_id)
    _seed_video(tenant_id, status="pending", published_at=None)

    fake = _FakeAsyncClient()
    with patch("workers.publisher_task.httpx.AsyncClient", lambda *a, **k: fake):
        auto_publish_scheduled_videos_task()

    my_posts = [p for p in fake.posts if p[1]["tenant_id"] == tenant_id]
    assert len(my_posts) == 0, "Videos pendientes/vencidos sin 'approved' no se publican"