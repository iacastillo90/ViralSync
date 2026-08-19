"""
test_competitor_ingest.py

Pruebas TDD del Competitor Benchmark (S4 — PR #4):
- T-S4-03: `index_winning_pattern` acepta `source`/`account_id` (default "own" =
  compat con analytics_agent) y mantiene el hash 384-d de `simple_embedding`;
  `get_winning_patterns` filtra por `source` (REQ-COMP-03, REQ-COMP-04).
- T-S4-04: `competitor_ingest.extract_hook_structure` (heurística determinista) e
  `ingest_competitor` (SearXNG cache 6h -> extractor -> Qdrant con
  source="competitor"), solo cuentas activas (REQ-COMP-02/03).

Se usan mocks de `_get_qdrant_client`/`asearxng_search_sanitized` (sin Qdrant/SearXNG
reales): las firmas y los payloads son el contrato verificado.
"""

import uuid

from unittest.mock import patch, MagicMock

from backend.db.models import CompetitorAccount
from backend.services.rag_context import simple_embedding, get_winning_patterns, index_winning_pattern
from backend.services.competitor_ingest import extract_hook_structure, ingest_competitor


def _captured_point(mock_upsert):
    """Devuelve (vector, payload) del primer PointStruct upsertado a Qdrant."""
    call = mock_upsert.call_args
    if "points" in call.kwargs:
        points = call.kwargs["points"]
    elif len(call.args) > 1:
        points = call.args[1]
    else:
        points = []
    assert points, "Se esperaba al menos un punto upsertado"
    return points[0].vector, points[0].payload


def _mock_qdrant_search(payloads):
    client = MagicMock()
    client.search.return_value = [MagicMock(payload=p) for p in payloads]
    return MagicMock(return_value=client)


# ---------------------------------------------------------------------------
# T-S4-03 — rag_context con fuente (source / account_id)
# ---------------------------------------------------------------------------


def test_index_winning_pattern_payload_includes_source_and_account_id():
    """REQ-COMP-03: payload con source="competitor" y account_id, y vector 384-d
    idéntico al de simple_embedding (mismo hash que rag_context)."""
    with patch("backend.services.rag_context._get_qdrant_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_collections.return_value.collections = []

        ok = index_winning_pattern(
            tenant_id="tenant_123",
            pattern_text="5 errores que debes evitar al entrenar",
            viral_score=0.82,
            niche="Fitness",
            source="competitor",
            account_id="account_1",
        )
        assert ok is True
        vector, payload = _captured_point(mock_client.upsert)
        assert payload["source"] == "competitor"
        assert payload["account_id"] == "account_1"
        assert len(vector) == 384
        assert vector == simple_embedding("Fitness 5 errores que debes evitar al entrenar")


def test_index_winning_pattern_default_source_own_does_not_break_analytics():
    """REQ-COMP-03: el default source="own" (y account_id None) mantiene la signatura
    que usa analytics_agent (que no pasa source ni account_id)."""
    with patch("backend.services.rag_context._get_qdrant_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_collections.return_value.collections = []

        ok = index_winning_pattern(
            tenant_id="tenant_123",
            pattern_text="Un gancho propio probado",
            viral_score=0.85,
            niche="Podcasting",
        )
        assert ok is True
        vector, payload = _captured_point(mock_client.upsert)
        assert payload["source"] == "own"
        assert payload["account_id"] is None
        assert len(vector) == 384


def test_get_winning_patterns_filters_by_source():
    """REQ-COMP-04: get_winning_patterns filtra por source; los patrones legacy (sin
    source, indexados por analytics_agent antes de S4) cuentan como 'own'."""
    factory = _mock_qdrant_search(
        [
            {"pattern_text": "A", "source": "own"},
            {"pattern_text": "B", "source": "competitor"},
            {"pattern_text": "C"},
            {"pattern_text": "D", "source": "competitor"},
        ]
    )
    with patch("backend.services.rag_context._get_qdrant_client", factory):
        comp = get_winning_patterns(niche="Fitness", query="gancho", limit=2, source="competitor")
        assert [p["pattern_text"] for p in comp] == ["B", "D"]

        own = get_winning_patterns(niche="Fitness", query="gancho", limit=2, source="own")
        assert [p["pattern_text"] for p in own] == ["A", "C"]

        all_patterns = get_winning_patterns(niche="Fitness", query="gancho", limit=4)
        assert len(all_patterns) == 4


# ---------------------------------------------------------------------------
# T-S4-04 — extract_hook_structure (heurística determinista) + ingest_competitor
# ---------------------------------------------------------------------------


def _competitor_account(**overrides) -> CompetitorAccount:
    fields = dict(
        id=str(uuid.uuid4()),
        tenant_id="tenant_123",
        platform="instagram",
        username="fitness_viral",
        display_name="Fitness Viral",
        niche="Fitness",
        is_active=True,
    )
    fields.update(overrides)
    return CompetitorAccount(**fields)


def test_extract_hook_structure_classifies_numeric_list():
    """REQ-COMP-03: un título numérico con palabra clave se clasifica como lista."""
    info = extract_hook_structure("5 errores que debes evitar al entrenar", "consejos rápidos")
    assert set(info) == {"title", "hook", "structure"}
    assert info["title"] == "5 errores que debes evitar al entrenar"
    assert info["structure"] == "Lista Numérica + Valor Exclusivo"


def test_extract_hook_structure_classifies_statistic_and_question():
    """REQ-COMP-03: estadística/porcentaje y pregunta retórica se clasifican."""
    stat = extract_hook_structure("¿Sabías que el 90% de las personas comete este error?", "")
    assert stat["structure"] == "Estadística / Porcentaje de Fricción"

    question = extract_hook_structure("¿Por qué tu contenido no despega?", "")
    assert question["structure"] == "Pregunta Retórica"

    interruption = extract_hook_structure("Stop de hacer esto si quieres resultados", "")
    assert interruption["structure"] == "Comando de Interrupción de Patrón"


def test_extract_hook_structure_default_and_fallback():
    """REQ-COMP-03: texto genérico cae en el default y sin inputs usa fallback."""
    generic = extract_hook_structure("Un día en la vida de un emprendedor", "snippet cualquiera")
    assert generic["structure"] == "General / Storytelling"

    empty = extract_hook_structure("", "")
    assert empty["hook"] == "gancho viral"
    assert empty["structure"] == "General / Storytelling"


def test_ingest_competitor_indexes_competitor_hooks():
    """REQ-COMP-02/03: ingest_competitor busca en SearXNG (cache 6h), extrae la
    estructura y la indexa en Qdrant con source='competitor' y el account_id."""
    account = _competitor_account()
    fake_results = [
        {"title": "5 errores que debes evitar al entrenar", "snippet": "consejos para crecer"},
        {"title": "¿Sabías que el 90% de las personas comete este error?", "snippet": "hook viral"},
        {"title": "", "snippet": ""},
    ]

    async def fake_search(query, num_results=5):
        assert num_results == 5
        assert "gancho viral" in query
        return fake_results

    indexed = []

    def fake_index(tenant_id, pattern_text, viral_score, niche="", source="own", account_id=None):
        indexed.append((pattern_text, source, account_id))
        return True

    with patch(
        "backend.services.competitor_ingest.asearxng_search_sanitized", fake_search
    ), patch("backend.services.competitor_ingest.index_winning_pattern", fake_index):
        import asyncio
        count = asyncio.run(ingest_competitor(account))

    assert count == 2, "Solo los 2 resultados con contenido deben indexarse"
    assert len(indexed) == 2
    for pattern_text, source, account_id in indexed:
        assert source == "competitor"
        assert account_id == account.id
        assert pattern_text, "El hook indexado no puede estar vacío"


def test_ingest_competitor_skips_inactive_account():
    """REQ-COMP-04 (escenario 2): cuenta inactiva no se indexa ni se busca."""
    account = _competitor_account(is_active=False)
    called = {"search": False, "index": False}

    async def fake_search(query, num_results=5):
        called["search"] = True
        return []

    def fake_index(*args, **kwargs):
        called["index"] = True
        return True

    with patch(
        "backend.services.competitor_ingest.asearxng_search_sanitized", fake_search
    ), patch("backend.services.competitor_ingest.index_winning_pattern", fake_index):
        import asyncio
        count = asyncio.run(ingest_competitor(account))

    assert count == 0
    assert called["search"] is False
    assert called["index"] is False


def test_ingest_competitor_returns_zero_on_no_results():
    """REQ-COMP-02: sin resultados de SearXNG no se indexa nada."""
    account = _competitor_account()
    indexed = []

    async def fake_search(query, num_results=5):
        return []

    def fake_index(*args, **kwargs):
        indexed.append(args)
        return True

    with patch(
        "backend.services.competitor_ingest.asearxng_search_sanitized", fake_search
    ), patch("backend.services.competitor_ingest.index_winning_pattern", fake_index):
        import asyncio
        count = asyncio.run(ingest_competitor(account))

    assert count == 0
    assert indexed == []