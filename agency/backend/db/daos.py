"""
daos.py

Capa de acceso a datos asíncrona (design D3, T-08): unit-of-work por llamada
sobre `AsyncSessionLocal` (backend/db/session.py). Cada DAO abre su propia
sesión, hace un único commit (per-node unit-of-work) y hace rollback explícito
ante error. Los nodos del grafo (WU-02b) llaman a estas funciones sin plomería
DB ad-hoc; `db_session` de los tests comparte el mismo motor SQLite (StaticPool)
y por eso ve las filas commiteadas.

Los dicts de los crews se mapean por whitelist a las columnas reales del DDL
(001/004) — convención DDL-as-truth: nunca se escribe una columna que no exista.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.db.models import Idea, Product, Script, Video

logger = logging.getLogger(__name__)


# Mapeo clave-del-crew → columna ORM (ideation_crew produce campos del LLM o del
# fallback; `passes_5_50` es clave interna del crew y NO existe en el DDL 001,
# la columna real es `passes_threshold`).
_IDEA_FIELD_TO_COLUMN: Dict[str, str] = {
    "texto": "texto",
    "gancho": "gancho",
    "entendible_nino_5_anos": "entendible_nino_5_anos",
    "interesa_50_de_100": "interesa_50_de_100",
    "universalidad": "universalidad",
    "intensidad": "intensidad",
    "claridad": "claridad",
    "shareability": "shareability",
    "distribucion": "distribucion",
    "alineacion": "alineacion",
    "rum_score": "rum_score",
    "passes_5_50": "passes_threshold",
}

_SCRIPT_FIELD_TO_COLUMN: Dict[str, str] = {
    "gancho_0_5s": "gancho_0_5s",
    "contexto_5_30s": "contexto_5_30s",
    "moraleja_30_50s": "moraleja_30_50s",
    "cta_50_60s": "cta_50_60s",
    "keyword": "keyword",
}


async def _run_with_commit(work: Callable[[AsyncSession], Any]) -> Any:
    """Abre una sesión propia, ejecuta `work(session)` y commitea.

    Un solo commit por llamada (unit-of-work por nodo); ante cualquier excepción
    hace rollback explícito y re-lanza para que el fallo sea honesto (PERSIST-02-2).
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await work(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


def _build_idea_row(tenant_id: str, idea: Dict[str, Any]) -> Idea:
    """Proyecta un dict candidato (crew) a una fila Idea del DDL 001 (whitelist)."""
    values = {
        column: idea[key]
        for key, column in _IDEA_FIELD_TO_COLUMN.items()
        if idea.get(key) is not None
    }
    return Idea(id=str(uuid.uuid4()), tenant_id=tenant_id, **values)


async def insert_ideas(tenant_id: str, ideas: List[Dict[str, Any]]) -> List[Idea]:
    """Persiste una fila `ideas` por candidato del nodo ideation (PERSIST-02-1).

    El `id` (UUID generado por el DAO) se devuelve en cada fila para que el state
    del grafo lo inyecte en los dicts y scriptwriting/approve puedan referenciarlo
    (design D3).
    """
    async def _work(session: AsyncSession) -> List[Idea]:
        rows = [_build_idea_row(tenant_id, idea) for idea in ideas]
        session.add_all(rows)
        await session.flush()
        return rows

    return await _run_with_commit(_work)


async def insert_script(
    tenant_id: str, idea_id: str, script: Dict[str, Any]
) -> Script:
    """Persiste un guion de 4 bloques con FK a la idea aprobada (PERSIST-02-1)."""
    async def _work(session: AsyncSession) -> Script:
        values = {
            column: script[key]
            for key, column in _SCRIPT_FIELD_TO_COLUMN.items()
            if script.get(key) is not None
        }
        row = Script(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            idea_id=idea_id,
            **values,
        )
        session.add(row)
        await session.flush()
        return row

    return await _run_with_commit(_work)


async def insert_video(
    tenant_id: str,
    script_id: str,
    raw_video_uri: str,
    edited_video_uri: str,
) -> Video:
    """Persiste una fila `videos` FK al script, capturando URIs crudo/editado (PERSIST-02-1)."""
    async def _work(session: AsyncSession) -> Video:
        row = Video(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            script_id=script_id,
            raw_video_uri=raw_video_uri,
            edited_video_uri=edited_video_uri,
            publish_approval_status="pending",
        )
        session.add(row)
        await session.flush()
        return row

    return await _run_with_commit(_work)


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def update_idea_approval(tenant_id: str, idea_id: str, status: str) -> bool:
    """Commit real de `approval_status` en ideas (PERSIST-03): True si actualizó 1 fila.

    El UPDATE va scoped por (id, tenant_id). Un idea_id no-UUID (p. ej. el id de
    e2e `"idea-e2e-001"`) es un no-op `False`, nunca un error (T-08 acceptance).
    """
    if not _is_uuid(idea_id):
        return False

    async def _work(session: AsyncSession) -> bool:
        result = await session.execute(
            update(Idea)
            .where(Idea.id == idea_id, Idea.tenant_id == tenant_id)
            .values(approval_status=status)
        )
        return result.rowcount > 0

    return await _run_with_commit(_work)


async def update_video_publish(
    tenant_id: str,
    video_id: str,
    post_id: str,
    published_at: datetime,
) -> bool:
    """Write-back del publish real sobre la fila `videos` (REQ-PTT-01 / D-F).

    Un único UPDATE atómico de `instagram_post_id` + `published_at` WHERE
    (id, tenant_id) — nunca un write parcial. `publish_approval_status` queda
    intacto (CHECK-safe: la DDL 001 sólo permite pending|approved|rejected,
    jamás 'published'). Un video_id no-UUID es un no-op `False`, nunca un error.
    """
    if not _is_uuid(video_id):
        return False

    async def _work(session: AsyncSession) -> bool:
        result = await session.execute(
            update(Video)
            .where(Video.id == video_id, Video.tenant_id == tenant_id)
            .values(instagram_post_id=post_id, published_at=published_at)
        )
        return result.rowcount > 0

    return await _run_with_commit(_work)


async def upsert_product(tenant_id: str, product: Dict[str, Any]) -> Product:
    """Upsert de la fila `products` por (tenant_id, name) — REQ-PERSIST-05 / D8.

    El product-ingest identifica al producto por su nombre: re-ingest con el mismo
    name actualiza description/product_image_url en vez de duplicar filas
    (no existe UNIQUE natural en el DDL 004; (tenant_id, name) es la clave lógica).

    PERSIST-05-1 / D-5: la fila guarda `object_key` — la key ESTABLE del objeto
    en MinIO, NUNCA la URL presignada (que expira). El write es None-safe: un
    re-upsert sin `object_key` conserva la key ya almacenada (SH-05-4 legacy);
    el INSERT inicial lo deja NULL si no viene (path TEXT_TO_VIDEO intacto,
    PERSIST-05-2).
    """
    async def _work(session: AsyncSession) -> Product:
        name = product.get("name")
        existing = (
            await session.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id, Product.name == name
                )
            )
        ).scalars().first()

        new_object_key = product.get("object_key")
        if existing is not None:
            existing.description = product.get("description", existing.description)
            existing.product_image_url = product.get(
                "product_image_url", existing.product_image_url
            )
            if new_object_key is not None:  # None-safe: conserva la key ya guardada
                existing.object_key = new_object_key
            row = existing
        else:
            row = Product(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                description=product.get("description"),
                product_image_url=product.get("product_image_url"),
                object_key=new_object_key,
            )
            session.add(row)
        await session.flush()
        return row

    return await _run_with_commit(_work)