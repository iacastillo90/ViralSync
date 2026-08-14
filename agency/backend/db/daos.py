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
from typing import Any, Callable, Dict, List, Optional

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


async def get_script_by_idea(tenant_id: str, idea_id: str) -> Optional[Script]:
    """Devuelve el guion más reciente de una idea, o None si aún no existe.

    PHASE-2 (dedup reactivación): al re-anudar una corrida ya terminada y
    re-aprobar una idea que ya tiene guion, `node_scriptwriting` reutiliza la
    fila existente en vez de insertar un duplicado (y evita gasto LLM).
    """
    async def _work(session: AsyncSession) -> Optional[Script]:
        return (
            await session.execute(
                select(Script)
                .where(Script.tenant_id == tenant_id, Script.idea_id == idea_id)
                .order_by(Script.created_at.desc())
                .limit(1)
            )
        ).scalars().first()

    return await _run_with_commit(_work)


async def insert_video(
    tenant_id: str,
    script_id: str,
    raw_video_uri: str,
    edited_video_uri: str,
    provider: Optional[str] = None,
) -> Video:
    """Persiste una fila `videos` FK al script, capturando URIs crudo/editado (PERSIST-02-1).

    ``provider`` ('json2video' | 'local') es opcional: cada variante generada
    para un mismo guion se persiste como su propia fila (dual-render, migración
    007). Las llamadas existentes que no lo pasan siguen funcionando.
    """
    async def _work(session: AsyncSession) -> Video:
        row = Video(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            script_id=script_id,
            raw_video_uri=raw_video_uri,
            edited_video_uri=edited_video_uri,
            provider=provider,
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


async def get_video_by_id(tenant_id: str, video_id: str) -> Optional[Video]:
    """Devuelve la fila `videos` por (id, tenant_id), o None si no existe.

    FASE-3 (elegir variante): el endpoint de aprobación y node_publish resuelven
    la variante elegida desde la DB (`edited_video_uri` real de ESA fila), nunca
    de un id no-UUID ni de otro tenant (anti-IDOR: siempre scoped por tenant_id).
    """
    if not _is_uuid(video_id):
        return None

    async def _work(session: AsyncSession) -> Optional[Video]:
        return (
            await session.execute(
                select(Video).where(Video.id == video_id, Video.tenant_id == tenant_id)
            )
        ).scalars().first()

    return await _run_with_commit(_work)


async def set_video_approval_status(tenant_id: str, video_id: str, status: str) -> bool:
    """Fija `publish_approval_status` de UNA fila `videos` por (id, tenant_id).

    FASE-3: la aprobación de publicación marca la variante elegida. Sólo admite
    los valores del CHECK 001 (pending|approved|rejected) — el call site decide
    cuál. Un video_id no-UUID es un no-op `False`, nunca un error (T-08).
    """
    if not _is_uuid(video_id):
        return False

    async def _work(session: AsyncSession) -> bool:
        result = await session.execute(
            update(Video)
            .where(Video.id == video_id, Video.tenant_id == tenant_id)
            .values(publish_approval_status=status)
        )
        return result.rowcount > 0

    return await _run_with_commit(_work)


async def reject_pending_sibling_variants(
    tenant_id: str, script_id: str, chosen_video_id: str
) -> int:
    """Marca como `rejected` las variantes PENDIENTES del mismo guion salvo la elegida.

    FASE-3 (política de marcado): al aprobar una variante, las demás del mismo
    `script_id` quedan `rejected` para que la elección sea unívoca en la DB. El
    WHERE exige `publish_approval_status='pending'`: filas ya aprobadas/rechazadas
    (ciclo previo de una re-aprobación) nunca se pisan. Devuelve nº de filas tocadas.
    """
    if not _is_uuid(script_id) or not _is_uuid(chosen_video_id):
        return 0

    async def _work(session: AsyncSession) -> int:
        result = await session.execute(
            update(Video)
            .where(
                Video.tenant_id == tenant_id,
                Video.script_id == script_id,
                Video.id != chosen_video_id,
                Video.publish_approval_status == "pending",
            )
            .values(publish_approval_status="rejected")
        )
        return result.rowcount or 0

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


from backend.db.models import Idea, Product, Script, Video, Tenant


async def upsert_product(tenant_id: str, product: Dict[str, Any]) -> Product:
    """Upsert de la fila `products` por (tenant_id, name) — REQ-PERSIST-05 / D8.

    El product-ingest identifica al producto por su nombre: re-ingest con el mismo
    name actualiza description/product_image_url en vez de duplicar filas.
    Garantiza la presencia del tenant en la tabla `tenants` para evitar violaciones de clave foránea.
    """
    async def _work(session: AsyncSession) -> Product:
        # 1. Asegurar que el tenant exista en DB (evitar FK IntegrityError)
        tenant_row = (
            await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalars().first()
        if tenant_row is None:
            import secrets
            tenant_row = Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                niche="Marketing General",
                litellm_virtual_key=f"sk-vs-{secrets.token_urlsafe(24)}",
                monthly_llm_budget_usd=20.00,
            )
            session.add(tenant_row)
            await session.flush()

        name = product.get("name")
        new_object_key = product.get("object_key")

        # REQ-PERSIST-05 / D8: upsert por (tenant_id, name) — re-ingest con el
        # mismo name actualiza descripción/imagen/object_key en vez de duplicar
        # filas. Restaurado tras 8267406 (refactor que lo eliminó por error).
        existing = (
            await session.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id, Product.name == name
                )
            )
        ).scalars().first()

        if existing is not None:
            if product.get("description") is not None:
                existing.description = product["description"]
            if product.get("product_image_url") is not None:
                existing.product_image_url = product["product_image_url"]
            if new_object_key is not None:  # None-safe: conserva la key ya guardada
                existing.object_key = new_object_key
            row = existing
        else:
            # Cada envío del formulario genera una nueva campaña/producto con su
            # ID y marca de tiempo propia (solo cuando el name es nuevo).
            row = Product(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                description=product.get("description"),
                product_image_url=product.get("product_image_url"),
                object_key=new_object_key,
                created_at=datetime.utcnow(),
            )
            session.add(row)
        await session.flush()
        return row

    return await _run_with_commit(_work)


async def get_latest_product(tenant_id: str) -> Optional[Product]:
    """Obtiene el último producto registrado por el tenant."""
    async def _work(session: AsyncSession) -> Optional[Product]:
        return (
            await session.execute(
                select(Product)
                .where(Product.tenant_id == tenant_id)
                .order_by(Product.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
    return await _run_with_commit(_work)


async def update_script_trend_score(
    tenant_id: str,
    script_id: str,
    score: float,
    rationale: str,
) -> bool:
    """
    Persiste el score de tendencias y su justificación en un guion existente.

    Migración 008: columnas `trend_score` y `trend_rationale`. El UPDATE siempre
    está scoped por (id, tenant_id) para evitar escrituras cross-tenant.
    Retorna True si actualizó exactamente 1 fila.
    """
    if not _is_uuid(script_id):
        return False

    async def _work(session: AsyncSession) -> bool:
        result = await session.execute(
            update(Script)
            .where(Script.id == script_id, Script.tenant_id == tenant_id)
            .values(
                trend_score=round(score, 2),
                trend_rationale=rationale[:300] if rationale else None,
            )
        )
        return result.rowcount > 0

    return await _run_with_commit(_work)


async def approve_script_and_idea(
    tenant_id: str,
    script_id: str,
    idea_id: str,
) -> Dict[str, bool]:
    """
    Aprueba un guion y su idea como pareja ganadora.

    Reglas de exclusión (migración 008):
      1. El guion `script_id` pasa a approval_status='approved'.
      2. La idea `idea_id` pasa a approval_status='approved'.
      3. TODOS los demás guiones del tenant que estén en 'pending' pasan a 'rejected'
         (excepto el aprobado), para que la UI los marque como descartados.
         Las otras ideas del tenant permanecen en su estado original (pending),
         dejándolas disponibles para que el cliente elija una en el futuro.

    Retorna dict: {'script_approved': bool, 'idea_approved': bool}
    """
    if not _is_uuid(script_id) or not _is_uuid(idea_id):
        return {"script_approved": False, "idea_approved": False}

    async def _work(session: AsyncSession) -> Dict[str, bool]:
        # 1. Aprobar el guion seleccionado
        r_script = await session.execute(
            update(Script)
            .where(Script.id == script_id, Script.tenant_id == tenant_id)
            .values(approval_status="approved")
        )
        # 2. Rechazar los demás guiones pending del tenant (exclusión)
        await session.execute(
            update(Script)
            .where(
                Script.tenant_id == tenant_id,
                Script.id != script_id,
                Script.approval_status == "pending",
            )
            .values(approval_status="rejected")
        )
        # 3. Aprobar la idea vinculada
        r_idea = await session.execute(
            update(Idea)
            .where(Idea.id == idea_id, Idea.tenant_id == tenant_id)
            .values(approval_status="approved")
        )
        return {
            "script_approved": r_script.rowcount > 0,
            "idea_approved": r_idea.rowcount > 0,
        }

    return await _run_with_commit(_work)


async def get_scripts_by_tenant(
    tenant_id: str,
    idea_id: Optional[str] = None,
) -> List[Script]:
    """
    Lista todos los guiones de un tenant, opcionalmente filtrados por idea_id.
    Incluye `approval_status` y `trend_score` (migración 008).
    """
    async def _work(session: AsyncSession) -> List[Script]:
        stmt = select(Script).where(Script.tenant_id == tenant_id)
        if idea_id and _is_uuid(idea_id):
            stmt = stmt.where(Script.idea_id == idea_id)
        stmt = stmt.order_by(Script.created_at.desc())
        return list((await session.execute(stmt)).scalars().all())

    return await _run_with_commit(_work)