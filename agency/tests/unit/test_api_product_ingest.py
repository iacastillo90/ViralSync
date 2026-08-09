"""
test_api_product_ingest.py

Acceptance WU-04 T-18 (REQ-PERSIST-05 / PERSIST-05-1/-2, design D8) sobre el
endpoint `POST /api/v1/tenants/{tenant_id}/product-ingest`:

- `test_product_ingest_no_file_returns_honest_empty_url`: sin archivo NO se
  fabrica un `product_image_url` (antes: default muerto
  `http://localhost:9000/viralsync-media/{tenant}/products/default_product.jpg`
  — URL de un objeto que no existe). La respuesta y la fila `products` quedan
  con string vacía, y el pipeline puede correr el path TEXT_TO_VIDEO
  (PERSIST-05-2).

Sigue el patrón de test_api_ideas_scripts_brain.py: AsyncClient + ASGITransport,
tenant UUID propio (espacio ffff…), `init_test_db` + `db_session`.
"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.main import app
from backend.security.auth import create_access_token
from backend.db.models import Tenant, Product


INGEST_TENANT_ID = "ffff0001-1111-2222-3333-444444444444"
# Nombre único por corrida: el upsert es por (tenant_id, name) — UUID evita
# colisión con filas de otros archivos en el DB compartido (StaticPool).
PRODUCT_NAME = f"Producto T-18 {uuid.uuid4().hex[:6]}"


def _auth_header(tenant_id: str, role: str = "admin") -> dict:
    token = create_access_token(user_id=f"user-test-{tenant_id}", tenant_id=tenant_id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ingest_tenant(db_session):
    """Crea el tenant del test si todavía no existe (patrón approve_tenant)."""
    existing = (
        await db_session.execute(select(Tenant.id).where(Tenant.id == INGEST_TENANT_ID))
    ).scalars().first()
    if existing is None:
        db_session.add(Tenant(id=INGEST_TENANT_ID, name="Ingest T-18 Tenant"))
        await db_session.commit()


@pytest.mark.anyio
async def test_product_ingest_no_file_returns_honest_empty_url(init_test_db, db_session, ingest_tenant):
    """T-18 / PERSIST-05-2: sin archivo → product_image_url vacío, nunca fabricado."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/tenants/{INGEST_TENANT_ID}/product-ingest",
            headers=_auth_header(INGEST_TENANT_ID),
            data={"product_name": PRODUCT_NAME, "description": "Un producto de test"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    # LA clave: honestidad — sin archivo no hay URL inventada de un objeto que no existe
    assert body["product_image_url"] == ""

    # La fila products quedó persistida con la URL vacía (REQ-PERSIST-05)
    row = (
        await db_session.execute(
            select(Product).where(
                Product.tenant_id == INGEST_TENANT_ID,
                Product.name == PRODUCT_NAME,
            )
        )
    ).scalars().first()
    assert row is not None
    assert row.product_image_url == ""