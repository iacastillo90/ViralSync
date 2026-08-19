"""
test_best_time.py

Pruebas unitarias del servicio `backend.services.best_time` (REQ-PUB-05).

Escenarios:
  1. Gemini responde -> slot persistido en `tenants.best_time_slot` con source='gemini'.
  2. Gemini falla/timeout -> slot heurístico de pico histórico persistido con
     source='heuristic'.
  3. La heurística pura elige el bucket (day_of_week, hour) con mayor views_72h.
  4. Sin historial de video_metrics -> slot por defecto determinístico.
"""

import asyncio
import uuid as uuid_mod
from datetime import datetime, timezone

from backend.db.models import Tenant, VideoMetric
from backend.db.session import AsyncSessionLocal, init_db
from backend.services import best_time


def run(coro):
    return asyncio.run(coro)


def _seed_tenant():
    """Crea un tenant fresco (aislado por test) y devuelve su id."""
    tenant_id = str(uuid_mod.uuid4())

    async def _run():
        await init_db()
        async with AsyncSessionLocal() as session:
            tenant = Tenant(id=tenant_id, name="Tenant best_time")
            session.add(tenant)
            await session.commit()

    run(_run())
    return tenant_id


def _seed_metrics(tenant_id, rows):
    """rows: lista de (views_72h, captured_at_utc_dt)."""

    async def _run():
        async with AsyncSessionLocal() as session:
            for views, captured_at in rows:
                session.add(
                    VideoMetric(
                        id=str(uuid_mod.uuid4()),
                        tenant_id=tenant_id,
                        video_id=str(uuid_mod.uuid4()),
                        views_72h=views,
                        captured_at=captured_at,
                    )
                )
            await session.commit()

    run(_run())


def _load_slot(tenant_id):
    async def _run():
        async with AsyncSessionLocal() as session:
            tenant = await session.get(Tenant, tenant_id)
            return tenant.best_time_slot

    return run(_run())


class _FakeLLM:
    """acomplete fake: devuelve el JSON dado o lanza la excepción dada."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def acomplete(self, messages, temperature=0.7, max_tokens=1000, **kwargs):
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.result


def test_heuristic_picks_peak_bucket():
    rows = [
        # Lunes 00:00 -> 10 views
        (10, datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc)),
        # Miércoles 20:00 -> 900 views (pico)
        (900, datetime(2026, 8, 19, 20, 0, tzinfo=timezone.utc)),
        # Miércoles 20:00 -> 100 views (mismo bucket, suma 1000)
        (100, datetime(2026, 8, 19, 20, 0, tzinfo=timezone.utc)),
        # Jueves 08:00 -> 300 views
        (300, datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)),
    ]
    slot = best_time._pick_heuristic_slot(rows)
    assert slot["day_of_week"] == 2, "Miércoles (weekday=2)"
    assert slot["hour"] == 20
    assert slot["source"] == "heuristic"
    # El valor debe reflejar la suma del bucket (900+100)
    assert slot["views_72h"] == 1000


def test_no_metrics_returns_default():
    slot = best_time._pick_heuristic_slot([])
    assert slot["source"] == "heuristic"
    assert 0 <= slot["day_of_week"] <= 6
    assert 0 <= slot["hour"] <= 23


def test_llm_slot_persisted_with_source_gemini(monkeypatch):
    tenant_id = _seed_tenant()
    _seed_metrics(tenant_id, [(50, datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc))])

    fake = _FakeLLM(result='{"day": 4, "hour": 20}')
    monkeypatch.setattr("agents.llm.acomplete", fake.acomplete)

    slot = run(best_time.suggest_best_time(tenant_id))
    assert slot["day_of_week"] == 4
    assert slot["hour"] == 20
    assert slot["source"] == "gemini"
    assert fake.calls, "El LLM debe invocarse con el prompt de agregados"
    # Persistido en el tenant
    assert _load_slot(tenant_id) == {
        "day_of_week": 4,
        "hour": 20,
        "source": "gemini",
    }


def test_llm_failure_falls_back_to_heuristic(monkeypatch):
    tenant_id = _seed_tenant()
    # Pico: Miércoles 20:00 (weekday=2) -> 1000 views
    _seed_metrics(
        tenant_id,
        [
            (1000, datetime(2026, 8, 19, 20, 0, tzinfo=timezone.utc)),
            (10, datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc)),
        ],
    )

    fake = _FakeLLM(error=RuntimeError("Gemini timeout"))
    monkeypatch.setattr("agents.llm.acomplete", fake.acomplete)

    slot = run(best_time.suggest_best_time(tenant_id))
    assert slot["source"] == "heuristic"
    assert slot["day_of_week"] == 2
    assert slot["hour"] == 20
    assert _load_slot(tenant_id)["source"] == "heuristic"


def test_llm_returning_garbage_falls_back(monkeypatch):
    tenant_id = _seed_tenant()
    _seed_metrics(tenant_id, [(40, datetime(2026, 8, 18, 9, 0, tzinfo=timezone.utc))])

    fake = _FakeLLM(result="no soy un json")
    monkeypatch.setattr("agents.llm.acomplete", fake.acomplete)

    slot = run(best_time.suggest_best_time(tenant_id))
    assert slot["source"] == "heuristic"