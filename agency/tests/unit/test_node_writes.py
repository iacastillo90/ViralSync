"""
test_node_writes.py

Node-level persistence tests for WU-02b (design D3/D8, REQ-PERSIST-02/05,
REQ-API-06). The production nodes (`node_ideation`, `node_scriptwriting`,
`node_video_edit`) must be `async def` and write through the async DAOs
(`insert_ideas` / `insert_script` / `insert_video` / `upsert_product`) instead
of only mutating in-memory state or swallowing DB errors:

- `test_node_ideation_persists_rows_and_injects_db_ids` — PERSIST-02-1 unit:
  one `ideas` row per candidate, and the DAO-generated `id` is injected into
  every idea dict + `selected_idea` so scriptwriting can FK it (design D3).
- `test_node_scriptwriting_persists_script_row` — PERSIST-02-1 unit: `scripts`
  row FK to the approved idea; the script id is injected into state so
  `node_video_edit` can FK it.
- `test_node_video_edit_persists_video_row` — PERSIST-02-1 unit: `videos` row
  FK to the script with raw/edited URIs captured.
- `test_graph_ainvoke_runs_async_nodes_and_persists` — the sync→async node
  contract risk (tasks.md risk table): a compiled LangGraph runs the async
  `node_ideation` and the rows land in the real tables.
- `test_node_ideation_upserts_product_when_image_url` — PERSIST-05-1: a run
  with `product_image_url` persists a `products` row (tenant FK).
- `test_node_ideation_no_product_skips_upsert` — PERSIST-05-2: no product →
  pipeline completes with zero `products` rows (graceful TEXT_TO_VIDEO).
- `test_node_ideation_dao_failure_fails_honestly` — PERSIST-02-2: a DAO write
  raising propagates out of the node (no silent state-only success).
- `test_get_ideas_and_scripts_return_node_written_rows` — REQ-API-06: the GET
  routers read the real tables, so rows written by the nodes are visible.

All tests run on the shared SQLite `db_session` fixture (StaticPool — the same
in-memory DB persists for the WHOLE pytest session, so EVERY write-test uses a
DEDICATED tenant id, following the repo convention that count assertions must
never collide with rows written by another test). The nodes open their own
`AsyncSessionLocal` (per-node unit-of-work) and rows are read back through the
fixture session, proving the shared in-memory DB contract. Crew functions are
mocked so the test never touches the LLM router or Search.
"""

import pytest
from sqlalchemy import select

from backend.db.models import Idea, Product, Script, Tenant, Video
from backend.db.daos import insert_ideas, insert_script

# Prefijo de filas propio de este archivo (dddd…) — ver docstring: el motor
# SQLite en memoria se comparte para TODA la sesión de pytest (StaticPool,
# conftest.py), así que cada test de escritura usa SU PROPIO tenant (sufijo 01-08)
# para que los conteos nunca colisionen con filas de otro test.
T_IDS = {
    "persist": "dddd0001-1111-2222-3333-444444444444",
    "script": "dddd0002-1111-2222-3333-444444444444",
    "video": "dddd0003-1111-2222-3333-444444444444",
    "graph": "dddd0004-1111-2222-3333-444444444444",
    "product_yes": "dddd0005-1111-2222-3333-444444444444",
    "product_no": "dddd0006-1111-2222-3333-444444444444",
    "honest": "dddd0007-1111-2222-3333-444444444444",
    "render_fail": "dddd0009-1111-2222-3333-444444444444",
    "get": "dddd0008-1111-2222-3333-444444444444",
    "video_id": "dddd0010-1111-2222-3333-444444444444",
    "publish_wb": "dddd0011-1111-2222-3333-444444444444",
    "rej_idea": "dddd0012-1111-2222-3333-444444444444",
    "rej_pub": "dddd0013-1111-2222-3333-444444444444",
    "rej_approve": "dddd0014-1111-2222-3333-444444444444",
    "rej_pending": "dddd0015-1111-2222-3333-444444444444",
    "ideation_empty": "dddd0016-1111-2222-3333-444444444444",
    "script_guard": "dddd0017-1111-2222-3333-444444444444",
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
async def node_tenants(db_session):
    """Garantiza los tenants de este archivo una sola vez (idempotente).

    Re-seedear el mismo tenants.id en cada test rompería UNIQUE; el fixture
    sólo inserta los tenants faltantes (patrón `dao_tenants` de test_daos.py).
    """
    existing = set(
        (await db_session.execute(select(Tenant.id).where(Tenant.id.in_(list(T_IDS.values()))))).scalars().all()
    )
    for i, (key, tid) in enumerate(T_IDS.items()):
        if tid not in existing:
            db_session.add(Tenant(id=tid, name=f"Node Tenant {key}"))
    await db_session.commit()


async def _fake_ideation_crew(niche, market_map):
    """Crew mockeada (async tras RELIABILITY-003): devuelve 2 candidatas sin `id`."""
    return [dict(IDEA_PAYLOAD), dict(IDEA_PAYLOAD, texto="La Verdad Incómoda sobre el SaaS")]


async def _fake_scriptwriting_crew(idea, niche_ppp=""):
    """Crew mockeada (async tras RELIABILITY-003): guion de 4 bloques sin `id`."""
    return dict(SCRIPT_PAYLOAD)


async def _fake_video_prompt_crew(script, idea, product_image_url=""):
    """Crew mockeada (async tras RELIABILITY-003): storyboard estático de 4 escenas."""
    return list(STORYBOARD_PAYLOAD)


class _FakePublishResponse:
    """Superficie mínima de httpx.Response para el publisher fake (2xx + id real)."""

    status_code = 201

    def raise_for_status(self):
        return None

    def json(self):
        return {"status": "published", "published_post_id": "ig_reel_write_back_001"}


class _FakePublishClient:
    """Sustituto local de httpx.AsyncClient para node_publish: POST → 2xx + id real."""

    def __init__(self, *, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None):
        return _FakePublishResponse()


@pytest.mark.anyio
async def test_node_ideation_persists_rows_and_injects_db_ids(db_session, node_tenants, monkeypatch):
    """PERSIST-02-1: tras node_ideation hay N filas y el id del DAO viaja en state."""
    from agents.nodes.ideation import node_ideation

    tenant_id = T_IDS["persist"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)

    result = await node_ideation(
        {
            "tenant_id": tenant_id,
            "niche": "Negocios B2B y SaaS",
            "market_map": {"errores": ["Falta de tracción"]},
            "logs": [],
        }
    )

    assert len(result["ideas"]) == 2
    # El id inyectado en cada idea dict proviene del DAO (D3, FK downstream)
    assert all(idea.get("id") for idea in result["ideas"])
    assert result["selected_idea"]["id"] == result["ideas"][0]["id"]

    persisted = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().all()
    assert len(persisted) == 2
    assert {i.texto for i in persisted} == {
        IDEA_PAYLOAD["texto"],
        "La Verdad Incómoda sobre el SaaS",
    }


@pytest.mark.anyio
async def test_node_scriptwriting_persists_script_row(db_session, node_tenants, monkeypatch):
    """PERSIST-02-1: node_scriptwriting persiste el guion FK a la idea en state."""
    from agents.nodes.scriptwriting import node_scriptwriting

    tenant_id = T_IDS["script"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]

    monkeypatch.setattr(
        "agents.nodes.scriptwriting.run_scriptwriting_crew",
        _fake_scriptwriting_crew,
    )

    result = await node_scriptwriting(
        {
            "tenant_id": tenant_id,
            "niche_ppp": "Escalar conversiones SaaS en 90 días",
            "selected_idea": {"id": idea_row.id, "texto": IDEA_PAYLOAD["texto"]},
            "logs": [],
        }
    )

    # La fila persiste FK a la idea aprobada
    persisted = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    assert len(persisted) == 1
    assert persisted[0].idea_id == idea_row.id
    assert persisted[0].keyword == SCRIPT_PAYLOAD["keyword"]
    # El id del guion se inyecta en state para que video_edit pueda FK
    assert result["script"]["id"] == persisted[0].id


@pytest.mark.anyio
async def test_node_video_edit_persists_video_row(db_session, node_tenants, monkeypatch):
    """PERSIST-02-1: node_video_edit persiste la fila videos con URIs reales."""
    from agents.nodes.video_edit import node_video_edit

    tenant_id = T_IDS["video"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(tenant_id, idea_row.id, SCRIPT_PAYLOAD)

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _fake_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )

    result = await node_video_edit(
        {
            "tenant_id": tenant_id,
            "script": {"id": script_row.id},
            "selected_idea": {"id": idea_row.id},
            "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
            "logs": [],
        }
    )

    persisted = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().all()
    assert len(persisted) == 1
    assert persisted[0].script_id == script_row.id
    assert persisted[0].raw_video_uri.endswith("raw_input.mp4")
    assert persisted[0].edited_video_uri.endswith("final.mp4")
    assert persisted[0].publish_approval_status == "pending"
    assert result["edited_video_uri"].endswith("final.mp4")


@pytest.mark.anyio
async def test_graph_ainvoke_runs_async_nodes_and_persists(db_session, node_tenants, monkeypatch):
    """Contracto sync→async: el grafo compilado corre el nodo async y persiste antes del interrupt."""
    from agents.graph import build_agency_graph
    from langgraph.checkpoint.memory import MemorySaver

    tenant_id = T_IDS["graph"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)

    app = build_agency_graph(checkpointer=MemorySaver())
    result = await app.ainvoke(
        {"tenant_id": tenant_id, "niche": "Fitness B2B", "market_map": {}, "logs": []},
        config={"configurable": {"thread_id": tenant_id}},
    )

    # El grafo se pausa en human_approval_idea: node_ideation ya corrió y persistió
    assert len(result.get("ideas", [])) == 2
    persisted = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().all()
    assert len(persisted) == 2
    assert {i.texto for i in persisted} == {
        IDEA_PAYLOAD["texto"],
        "La Verdad Incómoda sobre el SaaS",
    }


@pytest.mark.anyio
async def test_node_ideation_upserts_product_when_image_url(db_session, node_tenants, monkeypatch):
    """PERSIST-05-1: con product_image_url en state se persiste la fila products."""
    from agents.nodes.ideation import node_ideation

    tenant_id = T_IDS["product_yes"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)

    result = await node_ideation(
        {
            "tenant_id": tenant_id,
            "niche": "Negocios B2B y SaaS",
            "market_map": {},
            "product_name": "Suplemento Alpha Mind",
            "product_description": "Nootrópico natural",
            "product_image_url": "http://minio:9000/viralsync-media/alpha.png",
            "logs": [],
        }
    )

    assert len(result["ideas"]) == 2  # el pipeline sigue completo

    products = (
        await db_session.execute(select(Product).where(Product.tenant_id == tenant_id))
    ).scalars().all()
    assert len(products) == 1
    assert products[0].name == "Suplemento Alpha Mind"
    assert products[0].product_image_url.endswith("alpha.png")


@pytest.mark.anyio
async def test_node_ideation_no_product_skips_upsert(db_session, node_tenants, monkeypatch):
    """PERSIST-05-2: sin producto el nodo completa y NO escribe filas products."""
    from agents.nodes.ideation import node_ideation

    tenant_id = T_IDS["product_no"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)

    result = await node_ideation(
        {
            "tenant_id": tenant_id,
            "niche": "Negocios B2B y SaaS",
            "market_map": {},
            "logs": [],
        }
    )

    assert len(result["ideas"]) == 2  # pipeline completa por la vía TEXT_TO_VIDEO
    products = (
        await db_session.execute(select(Product).where(Product.tenant_id == tenant_id))
    ).scalars().all()
    assert products == []


@pytest.mark.anyio
async def test_node_ideation_dao_failure_fails_honestly(db_session, node_tenants, monkeypatch):
    """PERSIST-02-2: si el DAO falla, el nodo propaga el error (nunca éxito state-only)."""
    import agents.nodes.ideation as ideation_module
    from agents.nodes.ideation import node_ideation

    tenant_id = T_IDS["honest"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr(
        ideation_module,
        "insert_ideas",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db connection lost")),
    )

    with pytest.raises(RuntimeError, match="db connection lost"):
        await node_ideation(
            {
                "tenant_id": tenant_id,
                "niche": "Negocios B2B y SaaS",
                "market_map": {},
                "logs": [],
            }
        )

    # Honestidad: ningún falso éxito quedó persistido en las tablas reales
    rows = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().all()
    assert rows == []


@pytest.mark.anyio
async def test_node_video_edit_failed_render_propagates_honestly(db_session, node_tenants, monkeypatch):
    """RELIABILITY-001: si trigger_video_render devuelve status 'failed' (sin URL
    fabricada), node_video_edit propaga un RuntimeError y NO persiste ningún
    edited_video_uri falso en la fila `videos`."""
    from agents.nodes.video_edit import node_video_edit

    tenant_id = T_IDS["render_fail"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _fake_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {
            "status": "failed",
            "video_url": "",
            "message": "No real rendered video produced",
        },
    )

    with pytest.raises(RuntimeError, match="No real rendered video produced"):
        await node_video_edit(
            {
                "tenant_id": tenant_id,
                "script": {"id": idea_row.id},
                "selected_idea": {"id": idea_row.id},
                "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
                "logs": [],
            }
        )

    rows = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().all()
    assert rows == []  # no fila `videos` con un URI falso persistido


@pytest.mark.anyio
async def test_node_video_edit_exposes_video_id_from_insert_video(db_session, node_tenants, monkeypatch):
    """PTT-01/D-A: node_video_edit ya NO descarta la fila de `insert_video` — el
    `video_id` viaja en state para que node_publish pueda hacer el write-back."""
    from agents.nodes.video_edit import node_video_edit

    tenant_id = T_IDS["video_id"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(tenant_id, idea_row.id, SCRIPT_PAYLOAD)

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _fake_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )

    result = await node_video_edit(
        {
            "tenant_id": tenant_id,
            "script": {"id": script_row.id},
            "selected_idea": {"id": idea_row.id},
            "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
            "logs": [],
        }
    )

    persisted = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().all()
    assert len(persisted) == 1
    # El id del state ES el id de la fila `videos` persistida (D-A: fila real, no descartada)
    assert result["video_id"] == persisted[0].id


@pytest.mark.anyio
async def test_publish_write_back_persists_on_videos_row(db_session, node_tenants, monkeypatch):
    """PTT-01-1 (nivel DB, design D-F): node_publish persiste `instagram_post_id` +
    `published_at` en la fila `videos` vía `update_video_publish` — y NO toca
    `publish_approval_status`, que queda en el valor previo 'approved' (CHECK-safe:
    la DDL 001 sólo permite pending|approved|rejected — jamás 'published')."""
    from agents.nodes.video_edit import node_video_edit
    from agents.nodes.publish import node_publish
    import agents.nodes.publish as publish_module

    tenant_id = T_IDS["publish_wb"]
    idea_row = (await insert_ideas(tenant_id, [IDEA_PAYLOAD]))[0]
    script_row = await insert_script(tenant_id, idea_row.id, SCRIPT_PAYLOAD)

    monkeypatch.setattr(
        "agents.nodes.video_edit.run_video_prompt_crew",
        _fake_video_prompt_crew,
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    monkeypatch.setattr(publish_module, "AsyncClient", _FakePublishClient)

    # 1. node_video_edit persiste la fila `videos` (publish_approval_status='pending')
    edited = await node_video_edit(
        {
            "tenant_id": tenant_id,
            "script": {"id": script_row.id},
            "selected_idea": {"id": idea_row.id},
            "raw_video_uri": f"s3://viralsync-media-dev/{tenant_id}/raw_input.mp4",
            "logs": [],
        }
    )
    video_row = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().one()

    # 2. La aprobación de publicación (checkpoint humano previo al publish) deja la
    # fila en 'approved' — estado legal antes de publicar (CHECK-safe, spec risk note).
    video_row.publish_approval_status = "approved"
    await db_session.commit()

    # 3. node_publish: POST 2xx + post_id real → update_video_publish (write-back)
    await node_publish(
        {
            "tenant_id": tenant_id,
            "video_id": edited["video_id"],
            "edited_video_uri": edited["edited_video_uri"],
            "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
            "ig_user_id": "17841400000000001",
            "ig_access_token": "EAAXrealToken",
            "logs": [],
        }
    )

    # 4. Read-back vía SQLite: el write-back persistió dónde se publicó
    refreshed = (
        await db_session.execute(
            select(Video)
            .where(Video.id == edited["video_id"])
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.instagram_post_id == "ig_reel_write_back_001"
    assert refreshed.published_at is not None
    assert refreshed.publish_approval_status == "approved"  # jamás 'published' (CHECK 001)


@pytest.mark.anyio
async def test_get_ideas_and_scripts_return_node_written_rows(db_session, node_tenants, monkeypatch):
    """REQ-API-06: los GET leen las tablas reales → ven lo que escribieron los nodos."""
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from agents.nodes.ideation import node_ideation
    from agents.nodes.scriptwriting import node_scriptwriting

    tenant_id = T_IDS["get"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr(
        "agents.nodes.scriptwriting.run_scriptwriting_crew",
        _fake_scriptwriting_crew,
    )

    await node_ideation(
        {
            "tenant_id": tenant_id,
            "niche": "Negocios B2B y SaaS",
            "market_map": {},
            "logs": [],
        }
    )
    selected = (await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))).scalars().first()
    await node_scriptwriting(
        {
            "tenant_id": tenant_id,
            "selected_idea": {"id": selected.id, "texto": selected.texto},
            "logs": [],
        }
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ideas_res = await ac.get(f"/api/v1/tenants/{tenant_id}/ideas")
        scripts_res = await ac.get(f"/api/v1/tenants/{tenant_id}/scripts")

    assert ideas_res.status_code == 200
    assert scripts_res.status_code == 200
    ideas_body = ideas_res.json()
    scripts_body = scripts_res.json()
    assert len(ideas_body) == 2
    assert len(scripts_body) == 1
    assert {item["texto"] for item in ideas_body} == {
        IDEA_PAYLOAD["texto"],
        "La Verdad Incómoda sobre el SaaS",
    }
    assert scripts_body[0]["keyword"] == SCRIPT_PAYLOAD["keyword"]
    assert scripts_body[0]["idea_id"] == selected.id


# --------------------------------------------------------------------------- #
# Terminal topology (REQ-PTT-02 / D-B/D-C, TCK-004): rejection routes to the
# distinct terminal `term_rejected` (END) — FINAL per run; legal approval keeps
# the scriptwriting path unchanged (PTT-02-3); malformed resume re-pauses (D-C).
# --------------------------------------------------------------------------- #


async def _boom_scriptwriting_crew(idea, niche_ppp=""):
    """Crew que EXPLOTA si se invoca: tras un rechazo, scriptwriting jamás corre."""
    raise AssertionError("scriptwriting crew NO debe invocarse tras un rechazo (D-C)")


async def _boom_video_prompt_crew(script, idea, product_image_url=""):
    """Crew que EXPLOTA si se invoca: tras un rechazo de idea, video_edit jamás corre."""
    raise AssertionError("video_edit crew NO debe invocarse tras un rechazo (D-C)")


async def _tracking_scriptwriting_crew(idea, niche_ppp=""):
    """Crew mockeada que registra las invocaciones (para probar que el camino
    legal `approved` SI llega a scriptwriting, PTT-02-3)."""
    idea["_scriptwriting_invoked"] = True
    return dict(SCRIPT_PAYLOAD)


@pytest.mark.anyio
async def test_resume_rejected_idea_ends_term_rejected_no_script(db_session, node_tenants, monkeypatch):
    """PTT-02-1: resume con `idea_rejected=True` → el run termina en
    `term_rejected` (END), NO se crea fila `scripts`/`videos` y la crew de
    guionismo NUNCA se invoca (rechazo FINAL por run, PERSIST-03-2 reachable)."""
    from agents.graph import build_agency_graph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    tenant_id = T_IDS["rej_idea"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr("agents.nodes.scriptwriting.run_scriptwriting_crew", _boom_scriptwriting_crew)
    monkeypatch.setattr("agents.nodes.video_edit.run_video_prompt_crew", _boom_video_prompt_crew)

    app = build_agency_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": tenant_id}}

    # Run inicial: ideation persiste 2 ideas y el grafo se pausa en human_approval_idea
    await app.ainvoke(
        {"tenant_id": tenant_id, "niche": "Fitness B2B", "market_map": {}, "logs": []},
        config=cfg,
    )

    # Resume con señal POSITIVA de rechazo (D-B: nunca `idea_approved: False` = "not yet")
    result = await app.ainvoke(Command(update={"idea_rejected": True}), config=cfg)

    assert result.get("terminal_state") == "term_rejected"
    snapshot = await app.aget_state(cfg)
    assert snapshot.next == ()  # END alcanzado: sin nodos pendientes
    scripts = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    videos = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().all()
    assert scripts == []  # PERSIST-03-2 reachable: rechazo no crea guion
    assert videos == []  # y ningún video (el run cortó antes de scriptwriting)


@pytest.mark.anyio
async def test_resume_rejected_publish_ends_terminal_no_publish(db_session, node_tenants, monkeypatch):
    """PTT-02-2: resume con `publish_rejected=True` → term_rejected; el publisher
    NUNCA se invoca y NO hay write-back (REQ-PTT-01 no disparado)."""
    from agents.graph import build_agency_graph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    import agents.nodes.publish as publish_module

    tenant_id = T_IDS["rej_pub"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr("agents.nodes.scriptwriting.run_scriptwriting_crew", _fake_scriptwriting_crew)
    monkeypatch.setattr("agents.nodes.video_edit.run_video_prompt_crew", _fake_video_prompt_crew)
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )

    # Write-back y publisher: si node_publish corre, estos fakes explotan/registran
    wb_calls = []

    async def _fake_update_video_publish(*args, **kwargs):
        wb_calls.append(args)
        return True

    class _BoomPublishClient:
        def __init__(self, *, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            raise AssertionError("publisher NO debe invocarse tras rechazo de publicación (PTT-02-2)")

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(publish_module, "AsyncClient", _BoomPublishClient)
    monkeypatch.setattr(publish_module, "update_video_publish", _fake_update_video_publish, raising=False)

    app = build_agency_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": tenant_id}}

    await app.ainvoke(
        {"tenant_id": tenant_id, "niche": "Fitness B2B", "market_map": {}, "logs": []},
        config=cfg,
    )
    # Primer resume: aprobación legal de idea → scriptwriting + video_edit → pausa en publish
    await app.ainvoke(Command(update={"idea_approved": True, "idea_rejected": False}), config=cfg)
    snapshot = await app.aget_state(cfg)
    assert snapshot.next == ("human_approval_publish",)  # pausado en el checkpoint de publicación

    # Segundo resume: rechazo de publicación → terminal
    result = await app.ainvoke(Command(update={"publish_rejected": True}), config=cfg)

    assert result.get("terminal_state") == "term_rejected"
    assert wb_calls == []  # sin write-back (REQ-PTT-01 nunca disparado)
    scripts = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    assert len(scripts) == 1  # el guion aprobado existe, pero nada se publicó


@pytest.mark.anyio
async def test_resume_approved_idea_reaches_scriptwriting(db_session, node_tenants, monkeypatch):
    """PTT-02-3: resume legal `idea_approved=True` → el run avanza a scriptwriting
    y persiste el guion — la vía approved queda INTACTA (guard de regresión: si la
    topología rompe el camino legal, este test falla)."""
    from agents.graph import build_agency_graph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    tenant_id = T_IDS["rej_approve"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr("agents.nodes.scriptwriting.run_scriptwriting_crew", _tracking_scriptwriting_crew)
    monkeypatch.setattr("agents.nodes.video_edit.run_video_prompt_crew", _fake_video_prompt_crew)
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea, storyboard=None: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
    )

    app = build_agency_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": tenant_id}}

    await app.ainvoke(
        {"tenant_id": tenant_id, "niche": "Fitness B2B", "market_map": {}, "logs": []},
        config=cfg,
    )
    await app.ainvoke(Command(update={"idea_approved": True, "idea_rejected": False}), config=cfg)

    snapshot = await app.aget_state(cfg)
    assert snapshot.next == ("human_approval_publish",)  # avanzó más allá de scriptwriting

    scripts = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    assert len(scripts) == 1  # scriptwriting corrió y persistió el guion (aprobado)
    persisted_idea = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().first()
    assert scripts[0].idea_id == persisted_idea.id  # FK real a la idea aprobada


@pytest.mark.anyio
async def test_resume_pending_self_repauses(db_session, node_tenants, monkeypatch):
    """D-C fallback: resume malformado SIN flags positivos (`idea_approved: False` +
    `idea_rejected: False`) → el grafo se re-pausa en el MISMO checkpoint
    (pending→self), sin terminal y sin escribir guion. NOTA: este caso sólo es
    alcanzable vía payloads malformados — los endpoints siempre envían UNA señal."""
    from agents.graph import build_agency_graph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    tenant_id = T_IDS["rej_pending"]
    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _fake_ideation_crew)
    monkeypatch.setattr("agents.nodes.scriptwriting.run_scriptwriting_crew", _boom_scriptwriting_crew)

    app = build_agency_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": tenant_id}}

    await app.ainvoke(
        {"tenant_id": tenant_id, "niche": "Fitness B2B", "market_map": {}, "logs": []},
        config=cfg,
    )
    result = await app.ainvoke(Command(update={"idea_approved": False, "idea_rejected": False}), config=cfg)

    snapshot = await app.aget_state(cfg)
    assert snapshot.next == ("human_approval_idea",)  # re-pausado en el mismo checkpoint
    assert "terminal_state" not in result  # nunca terminal por un payload sin señal
    scripts = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    assert scripts == []


# --------------------------------------------------------------------------- #
# Empty-candidates honesty (REQ-PTT-03 / D-D, TCK-005): cero candidatas → error
# honesto NoCandidatesError ANTES de cualquier write (nunca IntegrityError).
# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_node_ideation_empty_candidates_raises_no_candidates_no_rows(db_session, node_tenants, monkeypatch):
    """PTT-03-1: la crew devuelve [] (cero ideas que pasan el filtro 5/50) →
    `NoCandidatesError(code='no_candidates')` se lanza ANTES de cualquier write;
    cero filas ideas/scripts/videos para el run; NUNCA IntegrityError."""
    from agents.nodes.ideation import node_ideation
    from agents.errors import NoCandidatesError

    tenant_id = T_IDS["ideation_empty"]

    async def _empty_ideation_crew(niche, market_map):
        return []

    monkeypatch.setattr("agents.nodes.ideation.run_ideation_crew", _empty_ideation_crew)

    with pytest.raises(NoCandidatesError) as exc_info:
        await node_ideation(
            {
                "tenant_id": tenant_id,
                "niche": "Negocios B2B y SaaS",
                "market_map": {},
                "logs": [],
            }
        )
    assert exc_info.value.code == "no_candidates"

    rows = (
        await db_session.execute(select(Idea).where(Idea.tenant_id == tenant_id))
    ).scalars().all()
    assert rows == []  # cero filas escritas para ese run (PTT-03-1)
    scripts = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    videos = (
        await db_session.execute(select(Video).where(Video.tenant_id == tenant_id))
    ).scalars().all()
    assert scripts == []
    assert videos == []


@pytest.mark.anyio
async def test_node_scriptwriting_missing_idea_id_raises(db_session, node_tenants, monkeypatch):
    """D-D (defensa en profundidad): `selected_idea` sin `id` → error honesto ANTES
    de llamar a `insert_script` (nunca IntegrityError por FK NULL), cero filas
    `scripts` escritas."""
    from agents.nodes.scriptwriting import node_scriptwriting

    tenant_id = T_IDS["script_guard"]
    monkeypatch.setattr("agents.nodes.scriptwriting.run_scriptwriting_crew", _fake_scriptwriting_crew)

    with pytest.raises(ValueError, match="selected_idea"):
        await node_scriptwriting(
            {
                "tenant_id": tenant_id,
                "niche_ppp": "Escalar conversiones SaaS en 90 días",
                "selected_idea": {},  # sin 'id' → no puede FK a una idea aprobada
                "logs": [],
            }
        )

    rows = (
        await db_session.execute(select(Script).where(Script.tenant_id == tenant_id))
    ).scalars().all()
    assert rows == []