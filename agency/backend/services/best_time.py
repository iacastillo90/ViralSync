"""
best_time.py

Servicio de sugerencia de mejor horario de publicación por tenant (REQ-PUB-05).

Doble vía:
  1. **Gemini** (vía `agents.llm.acomplete`, cuyo DIRECT_CHAIN prioriza Gemini):
     prompt acotado con los agregados de `video_metrics` (views_72h por
     day_of_week/hour) -> JSON ``{day, hour}``.
  2. **Fallback heurístico**: bucket ``(day_of_week, hour)`` con el pico
     histórico de views_72h, derivado de ``captured_at`` de ``video_metrics``
     (convención ``datetime.weekday()``: 0=Lunes .. 6=Domingo). Sin historial,
     se devuelve un slot por defecto determinístico.

Contrato: ``await suggest_best_time(tenant_id) -> {"day_of_week": int, "hour": int, "source": "gemini"|"heuristic"}``
El slot se persiste en ``tenants.best_time_slot`` (JSON).
"""

import json
import logging
import re
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy import select

import agents.llm as llm_router
from backend.db.models import Tenant, VideoMetric
from backend.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Slot por defecto (sin historial de video_metrics): Miércoles 19:00 UTC.
_DEFAULT_SLOT: Dict[str, Any] = {"day_of_week": 2, "hour": 19, "source": "heuristic"}

# Bucket por el que se agrupa el historial (convención datetime.weekday()).
_DAY_MIN, _DAY_MAX = 0, 6
_HOUR_MIN, _HOUR_MAX = 0, 23


def _pick_heuristic_slot(rows: Iterable[Tuple[int, Any]]) -> Dict[str, Any]:
    """Heurística pura: bucket (day_of_week, hour) con mayor suma de views_72h.

    :param rows: iterable de ``(views_72h, captured_at)``. ``captured_at`` es un
                 datetime (tz-naive o aware); se usa ``weekday()`` y ``hour``.
    :return: ``{"day_of_week", "hour", "views_72h", "source"}`` con
             ``source="heuristic"``. Sin filas -> slot por defecto.
    """
    buckets: Dict[Tuple[int, int], int] = {}
    for views, captured_at in rows:
        if captured_at is None:
            continue
        bucket = (captured_at.weekday(), captured_at.hour)
        buckets[bucket] = buckets.get(bucket, 0) + max(int(views or 0), 0)

    if not buckets:
        return dict(_DEFAULT_SLOT, views_72h=0)

    (day, hour), total = max(buckets.items(), key=lambda item: item[1])
    return {
        "day_of_week": day,
        "hour": hour,
        "views_72h": total,
        "source": "heuristic",
    }


def _aggregates_text(rows: List[Tuple[int, Any]]) -> str:
    """Texto compacto de agregados por bucket para el prompt del LLM."""
    buckets: Dict[Tuple[int, int], int] = {}
    for views, captured_at in rows:
        if captured_at is None:
            continue
        bucket = (captured_at.weekday(), captured_at.hour)
        buckets[bucket] = buckets.get(bucket, 0) + max(int(views or 0), 0)

    if not buckets:
        return "(sin datos históricos)"
    lines = sorted(f"day={day} hour={hour}: {total} views" for (day, hour), total in buckets.items())
    return "; ".join(lines)


async def _suggest_with_llm(aggregates_text: str) -> Tuple[int, int]:
    """Gemini -> JSON {day, hour}. Levanta excepción si falla o no parsea."""
    system_prompt = (
        "Eres un analista experto en engagement de contenido corto (Reels/TikTok). "
        "Dado el historial de reproducciones por día de la semana (0=Lunes..6=Domingo) "
        "y hora UTC, sugiere el MEJOR horario de publicación para el tenant. "
        "Devuelve ÚNICAMENTE un JSON con dos claves: \"day\" (int 0-6) y \"hour\" (int 0-23). "
        "Sin texto adicional."
    )
    user_prompt = (
        "Historial (views_72h agregadas por bucket day/hour UTC):\n"
        f"{aggregates_text}\n\n"
        "Devuelve el JSON:"
    )
    content = (
        await llm_router.acomplete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=64,
        )
    ).strip()

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"LLM response sin JSON: {content[:200]}")
    parsed = json.loads(match.group(0))
    day = int(parsed["day"])
    hour = int(parsed["hour"])
    if not (_DAY_MIN <= day <= _DAY_MAX) or not (_HOUR_MIN <= hour <= _HOUR_MAX):
        raise ValueError(f"Slot fuera de rango: day={day} hour={hour}")
    return day, hour


async def suggest_best_time(tenant_id: str) -> Dict[str, Any]:
    """Sugiere y persiste el mejor horario de publicación del tenant.

    1. Lee los agregados de ``video_metrics`` del tenant.
    2. Intenta Gemini; ante fallo/timeout/parse inválido -> heurística.
    3. Persiste ``tenants.best_time_slot`` (JSON) y devuelve el slot.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VideoMetric).where(VideoMetric.tenant_id == tenant_id)
        )
        metrics = result.scalars().all()
        rows = [(m.views_72h, m.captured_at) for m in metrics]

        aggregates_text = _aggregates_text(rows)
        try:
            day, hour = await _suggest_with_llm(aggregates_text)
            slot: Dict[str, Any] = {
                "day_of_week": day,
                "hour": hour,
                "source": "gemini",
            }
            logger.info("[best_time] Gemini sugirió day=%s hour=%s (tenant=%s)", day, hour, tenant_id)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del LLM cae a heurística
            heuristic = _pick_heuristic_slot(rows)
            slot = {k: heuristic[k] for k in ("day_of_week", "hour", "source")}
            logger.warning(
                "[best_time] LLM falló (%s); heurística -> day=%s hour=%s (tenant=%s)",
                exc,
                slot["day_of_week"],
                slot["hour"],
                tenant_id,
            )

        tenant = await session.get(Tenant, tenant_id)
        if tenant is not None:
            tenant.best_time_slot = slot
            await session.commit()
        else:
            logger.warning("[best_time] Tenant %s no existe; slot no persistido", tenant_id)

        return slot
