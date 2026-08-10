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


def _fake_ideation_crew(niche, market_map):
    """Crew mockeada: devuelve 2 candidatas sin `id` (el DAO genera el UUID)."""
    return [dict(IDEA_PAYLOAD), dict(IDEA_PAYLOAD, texto="La Verdad Incómoda sobre el SaaS")]


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
        lambda idea, niche_ppp="": dict(SCRIPT_PAYLOAD),
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
        lambda script, idea, product_image_url="": list(STORYBOARD_PAYLOAD),
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea: {"status": "completed", "video_url": f"http://static.viralsync/{tenant_id}/final.mp4"},
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
        lambda script, idea, product_image_url="": list(STORYBOARD_PAYLOAD),
    )
    monkeypatch.setattr(
        "agents.nodes.video_edit.trigger_video_render",
        lambda tenant_id, script, idea: {
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
        lambda idea, niche_ppp="": dict(SCRIPT_PAYLOAD),
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