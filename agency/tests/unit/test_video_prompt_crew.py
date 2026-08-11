"""
test_video_prompt_crew.py

Pruebas unitarias para el Agente CrewAI de Prompting Visual y Directiva de Cámara.

Slice 3 (PR #3, storage-honesty REQ-PERSIST-05 / SH-05-3/4/5): además de la crew,
cubre el graph path del `object_key` — `GraphRunRequest(product_object_key=...)`
→ state → `upsert_product` persiste la key; `node_video_edit` re-firma la key en
cada lectura (SH-05-3) o cae a la URL almacenada cuando no hay key (SH-05-4); la
firma de la crew NO cambia (SH-05-5). Zero-token: db_session SQLite + fakes.
"""

import asyncio
import json

import pytest
from sqlalchemy import select

from agents.crews import video_prompt_crew
from agents.crews.video_prompt_crew import run_video_prompt_crew
from agents.mcp_servers.video_gen_client import generate_storyboard_videos, VideoGenerationClient
from backend.db.models import Idea, Product, Script, Tenant
from backend.db.daos import insert_ideas, insert_script

LLM_STORYBOARD = json.dumps([
    {
        "scene_index": i,
        "timestamp_range": f"{i * 5}s - {(i + 1) * 5}s",
        "block_type": "gancho",
        "audio_text": "audio",
        "camera_shot": "Macro Close-Up",
        "visual_mode": "TEXT_TO_VIDEO",
        "visual_prompt": "9:16 vertical cinematic prompt for the scene",
    }
    for i in range(1, 5)
])


def test_video_prompt_crew_storyboard_generation():
    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert isinstance(storyboard, list)
    assert len(storyboard) == 4
    
    first_scene = storyboard[0]
    assert first_scene["block_type"] == "gancho"
    assert first_scene["timestamp_range"] == "0s - 5s"
    assert "visual_prompt" in first_scene
    assert "9:16" in first_scene["visual_prompt"]
    assert "camera_shot" in first_scene


def test_video_prompt_crew_injects_rum_threshold_and_trends(monkeypatch):
    # CVD-03-1 + CVD-04-1: prompt seam carries the Redis RUM threshold (0.78)
    # and the sanitized trend section when both are present.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_STORYBOARD

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        video_prompt_crew, "resolve_rum_threshold", lambda niche: 0.78
    )
    monkeypatch.setattr(
        video_prompt_crew, "build_trend_section", lambda niche: "- Reels virales SaaS 2026"
    )

    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert len(storyboard) == 4  # LLM path ran -> seam executed
    assert "0.78" in calls["user_prompt"]  # CVD-03-1
    assert "Reels virales SaaS 2026" in calls["user_prompt"]  # CVD-04-1


def test_video_prompt_crew_absent_context_non_fatal(monkeypatch):
    # CVD-03-2 + CVD-04-2: Redis down / cache miss -> clamp default injected,
    # trend section omitted, crew still produces its storyboard.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_STORYBOARD

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        video_prompt_crew, "resolve_rum_threshold", lambda niche: 0.70
    )
    monkeypatch.setattr(video_prompt_crew, "build_trend_section", lambda niche: "")

    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert len(storyboard) == 4  # crew still outputs
    assert "0.70" in calls["user_prompt"]  # CVD-03-2 clamp default injected
    assert "Trending topics" not in calls["user_prompt"]  # CVD-04-2 omitted


def test_video_gen_client_mock_provider():
    client = VideoGenerationClient(provider="mock")
    scene = {
        "scene_index": 1,
        "visual_prompt": "9:16 vertical video of modern futuristic office",
    }
    uri = client.generate_scene_video(scene, tenant_id="tenant-test")
    assert "mock_clip_scene_1.mp4" in uri


def test_generate_storyboard_videos():
    storyboard = [
        {"scene_index": 1, "visual_prompt": "Cinematic shot"},
        {"scene_index": 2, "visual_prompt": "Office shot"},
    ]
    result = generate_storyboard_videos(storyboard, tenant_id="tenant-demo")
    assert len(result) == 2
    assert "video_clip_uri" in result[0]


# --------------------------------------------------------------------------- #
# Slice 3 — graph path del object_key (REQ-PERSIST-05 / D-5, TSH-010):
# `GraphRunRequest.product_object_key` viaja al state → `node_ideation` lo
# persiste en `upsert_product`; `node_video_edit` re-firma la key en cada
# lectura (SH-05-3) o cae a la URL almacenada cuando no hay key (SH-05-4); la
# firma de la crew NO cambia (SH-05-5). Zero-token: db_session + crews fakes.
# --------------------------------------------------------------------------- #

# Espacio propio (eeee…): el DB SQLite se comparte para TODA la sesión pytest
# (StaticPool, conftest) — cada test de escritura usa SU tenant.
VIDEO_PATH_T_IDS = {
    "persist_key": "eeee0001-1111-2222-3333-444444444444",
    "resign": "eeee0002-1111-2222-3333-444444444444",
    "fallback": "eeee0003-1111-2222-3333-444444444444",
}

IDEA_PAYLOAD = {
    "texto": "3 Errores Críticos al Escalar SaaS en 2026",
    "gancho": "Si trabajas en SaaS, deja de cometer este error hoy mismo",
    "entendible_nino_5_anos": True,
    "interesa_50_de_100": True,
    "universalidad": 0.85,
    "intensidad": 0.9,
    "claridad": 0.95,
    "shareability": 0.8,
    "distribucion": 0.85,
    "alineacion": 0.9,
    "rum_score": 0.87,
    "passes_5_50": True,
}

SCRIPT_PAYLOAD = {
    "gancho_0_5s": "Tu equipo vende sin contenido",
    "contexto_5_30s": "El problema no es la falta de herramientas",
    "moraleja_30_50s": "Primero domina la tracción orgánica",
    "cta_50_60s": "Comenta CONSULTA abajo",
    "keyword": "CONSULTA",
}

STORYBOARD_PAYLOAD = [
    {"scene_index": 1, "prompt": "Hook scene", "start": 0, "end": 5},
    {"scene_index": 2, "prompt": "Context scene", "start": 5, "end": 30},
    {"scene_index": 3, "prompt": "Moral scene", "start": 30, "end": 50},
    {"scene_index": 4, "prompt": "CTA scene", "start": 50, "end": 60},
]


@pytest.fixture
async def video_path_tenants(db_session):
    """Garantiza los tenants de este archivo una sola vez (patrón node_tenants)."""
    existing = set(
        (
            await db_session.execute(
                select(Tenant.id).where(Tenant.id.in_(list(VIDEO_PATH_T_IDS.values())))
            )
        ).scalars().all()
    )
    for tid in VIDEO_PATH_T_IDS.values():
        if tid not in existing:
            db_session.add(Tenant(id=tid, name=f"VideoPath Tenant {tid[:8]}"))
    await db_session.commit()


async def _fake_ideation_crew(niche, market_map):
    """Crew mockeada: 2 candidatas sin `id` (el DAO lo inyecta)."""
    return [dict(IDEA_PAYLOAD), dict(IDEA_PAYLOAD, texto="La Verdad Incómoda sobre el SaaS")]


async def _fake_video_prompt_crew(script, idea, product_image_url=""):
    """Crew mockeada (firma con product_image_url, SH-05-5): storyboard estático."""
    return list(STORYBOARD_PAYLOAD)


def test_graph_run_request_accepts_product_object_key():
    """REQ-PERSIST-05 (slice 3): GraphRunRequest transporta `product_object_key`
    para que el backend guarde la key estable (no la URL) al persistir products."""
    from backend.routers.graph_execution import GraphRunRequest

    req = GraphRunRequest(product_object_key=f"{VIDEO_PATH_T_IDS['persist_key']}/products/foto.png")
    assert req.product_object_key == f"{VIDEO_PATH_T_IDS['persist_key']}/products/foto.png"


@pytest.mark.anyio
async def test_node_ideation_persists_object_key_when_in_state(db_session, video_path_tenants, monkeypatch):
    """PERSIST-05-1 (node): con `product_object_key` en state, `upsert_product`
    persiste la key estable en la fila `products` — no la URL presignada."""
    from agents.nodes.ideation import node_ideation

    tenant_id = VIDEO_PATH_T_IDS["persist_key"]
    object_key = f"{tenant_id}/products/alpha.png"
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)

    result = await node_ideation(
        {
            "tenant_id": tenant_id,
            "niche": "Negocios B2B y SaaS",
            "market_map": {},
            "product_name": "Suplemento Object Key",
            "product_description": "Nootrópico natural",
            "product_image_url": "http://minio:9000/viralsync-media/alpha.png?X-Amz-Signature=expired",
            "product_object_key": object_key,
            "logs": [],
        }
    )

    assert len(result["ideas"]) == 2  # pipeline sigue completo
    products = (
        await db_session.execute(select(Product).where(Product.tenant_id == tenant_id))
    ).scalars().all()
    assert len(products) == 1
    assert products[0].object_key == object_key  # la key estable, no la URL
    assert "X-Amz-Signature" not in products[0].object_key


@pytest.mark.anyio
async def test_node_video_edit_resigns_object_key_on_read(db_session, video_path_tenants, monkeypatch):
    """SH-05-3 (node): con `product_object_key` en state, node_video_edit re-firma
    la key (presign_public_url) y pasa la URL FRESCA a la crew — nunca la URL vieja."""
    from agents.nodes.video_edit import node_video_edit
    import agents.nodes.video_edit as video_edit_module

    tenant_id = VIDEO_PATH_T_IDS["resign"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(tenant_id, idea_row.id, SCRIPT_PAYLOAD)

    crew_calls = {}

    async def _tracking_video_prompt_crew(script, idea, product_image_url=""):
        crew_calls["product_image_url"] = product_image_url
        return list(STORYBOARD_PAYLOAD)

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _tracking_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )
    monkeypatch.setattr(
        video_edit_module,
        "presign_public_url",
        lambda object_key: f"http://127.0.0.1:9000/viralsync-media/{object_key}?X-Amz-Signature=fresh",
    )

    object_key = f"{tenant_id}/products/alpha.png"
    result = await node_video_edit(
        {
            "tenant_id": tenant_id,
            "script": {"id": script_row.id},
            "selected_idea": {"id": idea_row.id},
            "product_image_url": "http://minio:9000/viralsync-media/alpha.png?X-Amz-Signature=expired",
            "product_object_key": object_key,
            "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
            "logs": [],
        }
    )

    # SH-05-3: la crew recibe la URL re-firmada FRESCA, jamás la vieja del state
    assert "X-Amz-Signature=fresh" in crew_calls["product_image_url"]
    assert "X-Amz-Signature=expired" not in crew_calls["product_image_url"]
    assert result["edited_video_uri"].endswith("final.mp4")


@pytest.mark.anyio
async def test_node_video_edit_legacy_null_object_key_falls_back_to_stored_url(db_session, video_path_tenants, monkeypatch):
    """SH-05-4 (node): filas legacy sin `product_object_key` → se usa la URL
    almacenada tal cual (sin re-firma). El path TEXT_TO_VIDEO no se rompe."""
    from agents.nodes.video_edit import node_video_edit
    import agents.nodes.video_edit as video_edit_module

    tenant_id = VIDEO_PATH_T_IDS["fallback"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(tenant_id, idea_row.id, SCRIPT_PAYLOAD)

    crew_calls = {}

    async def _tracking_video_prompt_crew(script, idea, product_image_url=""):
        crew_calls["product_image_url"] = product_image_url
        return list(STORYBOARD_PAYLOAD)

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _tracking_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )

    stored_url = "http://minio:9000/viralsync-media/legacy.png?X-Amz-Signature=old"
    await node_video_edit(
        {
            "tenant_id": tenant_id,
            "script": {"id": script_row.id},
            "selected_idea": {"id": idea_row.id},
            "product_image_url": stored_url,  # sin product_object_key (legacy)
            "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
            "logs": [],
        }
    )

    # SH-05-4: cae a la URL almacenada sin re-firma (presign_public_url NO se usa)
    assert crew_calls["product_image_url"] == stored_url


def test_run_video_prompt_crew_signature_unchanged():
    """SH-05-5: la firma pública de la crew NO cambia con el slice 3 —
    (script, idea, product_image_url=''). video_prompt_crew.py queda intacto."""
    import inspect

    sig = inspect.signature(run_video_prompt_crew)
    params = list(sig.parameters)
    assert params == ["script", "idea", "product_image_url"]
    assert sig.parameters["product_image_url"].default == ""
