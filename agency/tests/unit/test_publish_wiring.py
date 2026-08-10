"""
test_publish_wiring.py

Publish wiring tests for WU-04 (design D5, REQ-PUBLISH-01/02, REQ-API-06):
`agents/nodes/publish.py` must be an `async def` node connected to the REAL
publisher contract over HTTP (`PUBLISHER_URL`, default `http://localhost:8002`)
instead of the old in-process adapter call with fabricated defaults:

- `test_node_publish_no_tokens_raises_security_error` — PUBLISH-02-3 /
  PUBLISH-01-2: sin `ig_user_id`/`ig_access_token` en state → ValueError honesto
  y NO se hace ninguna llamada HTTP (ni id inventado).
- `test_node_publish_calls_publisher_http` — PUBLISH-02-1: token real → POST
  `{PUBLISHER_URL}/publish` con tenant_id/video_url/caption/credenciales y el
  `published_post_id` devuelto es el REAL de la respuesta (nunca fabricado).
- `test_node_publish_no_edited_uri_raises` — T-00 #3: se eliminó el default
  muerto `s3://…`; sin `edited_video_uri` el nodo falla honesto.
- `test_node_publish_dev_token_simulated` — PUBLISH-02-2: token `token_` (dev)
  conserva la simulación honesta del micro (adapters): el id simulado viene del
  contrato publisher, el nodo NO fabrica nada.
- `test_node_publish_publisher_down_raises_honest_error` — D5: `:8002` caído →
  RuntimeError claro, sin simulación.
- `test_node_publish_response_without_id_never_fabricates` — anti-fabricación:
  respuesta sin `published_post_id` → error; jamás `post_…`/`ig_reel_…` inventados.
- `test_node_publish_source_has_no_fabricated_defaults` — T-16 acceptance:
  el fuente del nodo no contiene defaults fabricados (`post_{` o `s3://`).

Mocking: httpx.AsyncClient se reemplaza por un fake con context-manager que
registra las llamadas y devuelve la respuesta configurada — el nodo nunca toca
red en estos tests (la simulación dev vive en el adaptador del micro, probada
en test_audit_findings_resolutions.py).
"""

import inspect

import httpx
import pytest

from agents.nodes import publish as publish_module


class FakeResponse:
    """Superficie mínima de httpx.Response usada por el nodo."""

    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "http://publisher"),
                response=httpx.Response(self.status_code, request=httpx.Request("POST", "http://publisher")),
            )

    def json(self):
        return self._payload


class FakeAsyncClient:
    """Sustituto de httpx.AsyncClient: registra POSTs y devuelve la respuesta configurada."""

    def __init__(self, *, timeout=None):
        self.timeout = timeout
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None):
        self.calls.append((url, json))
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response


@pytest.fixture
def fake_http(monkeypatch):
    """Instala FakeAsyncClient en el módulo del nodo y expone el estado del fake."""
    state = {
        "instance": None,
        "raise_exc": None,
        "response": None,
        "clients": [],
    }

    def _factory(*, timeout=None):
        client = FakeAsyncClient(timeout=timeout)
        client._response = state["response"]
        client._raise_exc = state["raise_exc"]
        state["instance"] = client
        state["client"] = client
        state["clients"].append(client)
        return client

    monkeypatch.setattr(publish_module, "AsyncClient", _factory)
    return state


@pytest.mark.anyio
async def test_node_publish_no_tokens_raises_security_error(fake_http, monkeypatch):
    """PUBLISH-02-3: sin credenciales → error de seguridad; sin llamada HTTP; sin id."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    from agents.nodes.publish import node_publish

    with pytest.raises(ValueError, match="ausente"):
        await node_publish(
            {
                "tenant_id": "t-pub-01",
                "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-01/final.mp4",
                "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
                "logs": [],
            }
        )

    assert fake_http["instance"] is None  # el nodo NO llamó al publisher


@pytest.mark.anyio
async def test_node_publish_calls_publisher_http(fake_http, monkeypatch):
    """PUBLISH-02-1: token real → POST a :8002 con el contrato y devuelve el id REAL."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(
        201,
        {
            "status": "published",
            "published_post_id": "ig_reel_real_from_graph_api",
            "tenant_id": "t-pub-02",
            "platform": "instagram",
        },
    )
    from agents.nodes.publish import node_publish

    result = await node_publish(
        {
            "tenant_id": "t-pub-02",
            "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-02/final.mp4",
            "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
            "ig_user_id": "17841400000000001",
            "ig_access_token": "EAAXrealToken",
            "logs": [],
        }
    )

    assert result["published_post_id"] == "ig_reel_real_from_graph_api"
    assert fake_http["instance"] is not None
    url, payload = fake_http["instance"].calls[0]
    assert url == "http://test-publisher:8002/publish"
    assert payload["tenant_id"] == "t-pub-02"
    assert payload["video_url"].endswith("final.mp4")
    assert payload["caption"] == "Hook\n\nCTA"
    assert payload["instagram_user_id"] == "17841400000000001"
    assert payload["access_token"] == "EAAXrealToken"


@pytest.mark.anyio
async def test_node_publish_no_edited_uri_raises(fake_http):
    """T-00 #3: el default s3:// se eliminó — sin edited_video_uri el nodo falla honesto."""
    from agents.nodes.publish import node_publish

    with pytest.raises(ValueError, match="edited_video_uri"):
        await node_publish(
            {
                "tenant_id": "t-pub-03",
                "ig_user_id": "17841400000000001",
                "ig_access_token": "token_x",
                "logs": [],
            }
        )

    assert fake_http["instance"] is None


@pytest.mark.anyio
async def test_node_publish_dev_token_simulated(fake_http, monkeypatch):
    """PUBLISH-02-2: token_ (dev) → el id simulado lo emite el publisher (adapters), no el nodo."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(
        201,
        {
            "status": "published",
            "published_post_id": "ig_reel_t-pub-04_1234567890",  # sim del micro en dev
            "tenant_id": "t-pub-04",
            "platform": "instagram",
        },
    )
    from agents.nodes.publish import node_publish

    result = await node_publish(
        {
            "tenant_id": "t-pub-04",
            "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-04/final.mp4",
            "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
            "ig_user_id": "17841400000000001",
            "ig_access_token": "token_dev_simulado",
            "logs": [],
        }
    )

    assert result["published_post_id"] == "ig_reel_t-pub-04_1234567890"
    _, payload = fake_http["instance"].calls[0]
    assert payload["access_token"] == "token_dev_simulado"
    assert result["logs"][-1].startswith("[publish]")


@pytest.mark.anyio
async def test_node_publish_publisher_down_raises_honest_error(fake_http, monkeypatch):
    """D5: publisher caído → error claro, sin simulación ni id."""

    class _ConnRefused(httpx.ConnectError):
        def __init__(self):
            super().__init__("All connection attempts failed: [Errno 111] Connection refused")

    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["raise_exc"] = _ConnRefused()

    from agents.nodes.publish import node_publish

    with pytest.raises(RuntimeError, match="Publisher"):
        await node_publish(
            {
                "tenant_id": "t-pub-05",
                "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-05/final.mp4",
                "script": {},
                "ig_user_id": "17841400000000001",
                "ig_access_token": "EAAXrealToken",
                "logs": [],
            }
        )


@pytest.mark.anyio
async def test_node_publish_response_without_id_never_fabricates(fake_http, monkeypatch):
    """Anti-fabricación: respuesta sin published_post_id → error; jamás post_... inventado."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(201, {"status": "published", "tenant_id": "t-pub-06"})
    from agents.nodes.publish import node_publish

    with pytest.raises(RuntimeError, match="published_post_id"):
        await node_publish(
            {
                "tenant_id": "t-pub-06",
                "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-06/final.mp4",
                "script": {},
                "ig_user_id": "17841400000000001",
                "ig_access_token": "EAAXrealToken",
                "logs": [],
            }
        )


@pytest.mark.anyio
async def test_node_publish_sends_stable_idempotency_key(fake_http, monkeypatch):
    """RESILIENCE-001: el payload lleva una idempotency_key estable — un retry del
    MISMO publish manda la MISMA key (el micro puede dedupear y no duplicar)."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(
        201,
        {
            "status": "published",
            "published_post_id": "ig_reel_real",
            "tenant_id": "t-pub-07",
            "platform": "instagram",
        },
    )
    from agents.nodes.publish import node_publish

    state = {
        "tenant_id": "t-pub-07",
        "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-07/final.mp4",
        "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
        "ig_user_id": "17841400000000001",
        "ig_access_token": "EAAXrealToken",
        "logs": [],
    }

    await node_publish(dict(state))
    await node_publish(dict(state))  # retry del mismo publish

    keys = [calls[1]["idempotency_key"] for client in fake_http["clients"] for calls in client.calls]
    assert len(keys) == 2
    assert keys[0] == keys[1]  # estable: el micro puede dedupear el retry


def test_node_publish_source_has_no_fabricated_defaults():
    """T-16 acceptance: el nodo ya no contiene defaults fabricados (f"post_{" / f"s3://")."""
    from agents.nodes.publish import node_publish

    src = inspect.getsource(node_publish)
    assert 'f"post_{' not in src
    assert 'f"s3://' not in src


# --------------------------------------------------------------------------- #
# Publish write-back (REQ-PTT-01 / D-F): un único UPDATE atómico tras 2xx + id
# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_node_publish_persists_write_back_after_2xx(fake_http, monkeypatch):
    """PTT-01-1: tras POST 2xx + post_id real, `update_video_publish` se llama
    EXACTAMENTE una vez con `(tenant_id, video_id, post_id, published_at)` — el
    write-back persiste dónde se publicó (REQ-PTT-01, design D-F)."""
    from datetime import datetime

    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(
        201,
        {
            "status": "published",
            "published_post_id": "ig_reel_write_back_real",
            "tenant_id": "t-pub-08",
            "platform": "instagram",
        },
    )

    calls = []
    monkeypatch.setattr(
        publish_module,
        "update_video_publish",
        lambda tenant_id, video_id, post_id, published_at: (
            calls.append((tenant_id, video_id, post_id, published_at)) or True
        ),
        raising=False,
    )
    from agents.nodes.publish import node_publish

    await node_publish(
        {
            "tenant_id": "t-pub-08",
            "video_id": "dddd0003-1111-2222-3333-444444444444",
            "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-08/final.mp4",
            "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
            "ig_user_id": "17841400000000001",
            "ig_access_token": "EAAXrealToken",
            "logs": [],
        }
    )

    assert len(calls) == 1  # un único UPDATE atómico, nunca dos (D-F)
    tenant_id, video_id, post_id, published_at = calls[0]
    assert tenant_id == "t-pub-08"
    assert video_id == "dddd0003-1111-2222-3333-444444444444"
    assert post_id == "ig_reel_write_back_real"
    assert isinstance(published_at, datetime)
    assert published_at.tzinfo is not None  # timestamp utc-aware persistible


@pytest.mark.anyio
async def test_node_publish_skips_write_back_without_video_id(fake_http, monkeypatch):
    """PTT-01-3: state sin `video_id` (replay/resume) → publish OK, sin UPDATE,
    sin crash — nunca se fabrica un write-back (D-F: `if not video_id: skip`)."""
    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["response"] = FakeResponse(
        201,
        {
            "status": "published",
            "published_post_id": "ig_reel_replay_no_video_id",
            "tenant_id": "t-pub-09",
            "platform": "instagram",
        },
    )

    calls = []
    monkeypatch.setattr(
        publish_module,
        "update_video_publish",
        lambda *args, **kwargs: calls.append(args) or True,
        raising=False,
    )
    from agents.nodes.publish import node_publish

    result = await node_publish(
        {
            "tenant_id": "t-pub-09",
            "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-09/final.mp4",
            "script": {"gancho_0_5s": "Hook", "cta_50_60s": "CTA"},
            "ig_user_id": "17841400000000001",
            "ig_access_token": "EAAXrealToken",
            "logs": [],
        }
    )

    assert result["published_post_id"] == "ig_reel_replay_no_video_id"
    assert calls == []  # sin video_id ⇒ cero UPDATEs (PTT-01-3)


@pytest.mark.anyio
async def test_node_publish_failure_never_writes_back(fake_http, monkeypatch):
    """PTT-01-2: publisher falla → node_publish raise; `update_video_publish` NUNCA
    se invoca — no existe write parcial (D-F: el UPDATE sólo corre tras 2xx + id)."""

    class _ConnRefused(httpx.ConnectError):
        def __init__(self):
            super().__init__("All connection attempts failed: [Errno 111] Connection refused")

    monkeypatch.setattr(publish_module, "PUBLISHER_URL", "http://test-publisher:8002")
    fake_http["raise_exc"] = _ConnRefused()

    calls = []
    monkeypatch.setattr(
        publish_module,
        "update_video_publish",
        lambda *args, **kwargs: calls.append(args) or True,
        raising=False,
    )
    from agents.nodes.publish import node_publish

    with pytest.raises(RuntimeError, match="Publisher"):
        await node_publish(
            {
                "tenant_id": "t-pub-10",
                "video_id": "dddd0003-1111-2222-3333-444444444444",
                "edited_video_uri": "http://minio:9000/viralsync-media/t-pub-10/final.mp4",
                "script": {},
                "ig_user_id": "17841400000000001",
                "ig_access_token": "EAAXrealToken",
                "logs": [],
            }
        )

    assert calls == []  # raise ⇒ sin write-back; la fila queda intacta (PTT-01-2)