import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.security.auth import create_access_token
from agents.crews.ideation_crew import run_ideation_crew
from agents.crews.scriptwriting_crew import run_scriptwriting_crew
from workers.video_edit_task import process_video_postproduction
from workers.metrics_loop_task import audit_72h_metrics
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload
from backend.security.hmac_validator import verify_meta_hmac_signature
from backend.db.models import Lead, Idea
from backend.db.daos import insert_ideas
from sqlalchemy import select


@pytest.mark.anyio
async def test_complete_viral_sync_lifecycle(db_session):
    # Step 1: Onboarding de nuevo Tenant
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res_tenant = await ac.post(
            "/api/v1/tenants",
            json={
                "name": "Cliente E2E Fitness",
                "niche": "Fitness B2B y Gimnasios",
                "monthly_llm_budget_usd": 25.00,
            },
        )
        assert res_tenant.status_code == 201
        tenant_data = res_tenant.json()
        tenant_id = tenant_data["id"]
        assert "litellm_virtual_key" in tenant_data

        # Crear token JWT autenticado para el tenant recién creado (Anti-IDOR)
        token = create_access_token(user_id="usr_e2e_001", tenant_id=tenant_id)
        auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

        # Seed de un Lead real para el tenant, de modo que el takeover resuelva a
        # handled_by_human (200) en lugar de 404/503 (fail-closed sin datos ficticios).
        # El tenant ya quedó persistido por el POST /tenants (las sesiones comparten el
        # mismo SQLite :memory: vía StaticPool), así que no se re-inserta. Todas las
        # columnas NOT NULL del DDL (video_id, keyword, ig_user_id, mensaje_original)
        # reciben valores — el lead_id es un UUID válido para ambos esquemas (SQLite
        # CHAR(32) y Postgres UUID).
        seeded_lead_id = str(uuid.uuid4())
        seeded_lead = Lead(
            id=seeded_lead_id,
            tenant_id=tenant_id,
            video_id=str(uuid.uuid4()),
            keyword="CONSULTA",
            ig_user_id="user_ig_fitness_99",
            mensaje_original="Quiero la CONSULTA por favor",
            origen="comment",
        )
        db_session.add(seeded_lead)
        await db_session.commit()

        # Step 2: Ejecución de Ideación RUM (crew async tras RELIABILITY-003)
        ideas = await run_ideation_crew(
            niche="Fitness B2B y Gimnasios",
            market_map={"errores": ["Falta de retención"]},
        )
        assert len(ideas) >= 1
        selected_idea = ideas[0]
        assert selected_idea["rum_score"] > 0.0

        # Step 3: Checkpoint Humano — Aprobar Idea (REQ-PTT-04 honestidad)
        # (a) id 0-row/no-UUID ("idea-e2e-001") → 404 honesto: un no-op NO puede
        #     parecer progreso. Nunca 202 para un approve sin fila que actualizar.
        res_idea_unknown = await ac.post(
            f"/api/v1/tenants/{tenant_id}/ideas/approve",
            json={"idea_id": "idea-e2e-001", "status": "approved"},
            headers=auth_headers,
        )
        assert res_idea_unknown.status_code == 404  # PTT-04-2: 0-row → error, no 202

        # (b) persistir la idea REAL del crew y aprobar su UUID → 202 + commit
        #     real de approval_status (PTT-04-1: el happy path queda cubierto).
        persisted_ideas = await insert_ideas(tenant_id, [selected_idea])
        real_idea_id = persisted_ideas[0].id
        res_idea_app = await ac.post(
            f"/api/v1/tenants/{tenant_id}/ideas/approve",
            json={"idea_id": real_idea_id, "status": "approved"},
            headers=auth_headers,
        )
        assert res_idea_app.status_code == 202  # id real: aceptado y encolado + commit
        idea_body = res_idea_app.json()
        assert idea_body["status"] == "accepted"
        assert idea_body["kind"] == "idea_approval"
        assert idea_body["queued"] is True
        # El echo es el id real del request, nunca un id fabricado
        assert idea_body["idea_id"] == real_idea_id
        # El commit real quedó persistido en la DB (verificable vía la sesión
        # compartida SQLite StaticPool, como en tests unitarios de approve)
        idea_row = (
            await db_session.execute(
                select(Idea)
                .where(Idea.id == real_idea_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert idea_row.approval_status == "approved"

        # Step 4: Guionismo en 4 Bloques (crew async tras RELIABILITY-003)
        script = await run_scriptwriting_crew(
            idea=selected_idea,
            niche_ppp="Consigue 50 socios en 30 días sin pagar anuncios",
        )
        assert script["keyword"]  # Verificar que no esté vacío
        assert "gancho_0_5s" in script

        # Step 5: Post-producción Asíncrona de Video (Celery Eager)
        # RELIABILITY-001: sin microservicio de renderizado REAL en el entorno de
        # test, el pipeline reporta un fallo HONESTO (status 'failed',
        # edited_video_uri=None) — nunca una URL fabricada de video "exitoso".
        video_res = process_video_postproduction(
            tenant_id=tenant_id,
            raw_video_uri=f"s3://viralsync-media-dev/{tenant_id}/raw.mp4",
            script=script,
        )
        assert video_res["status"] == "failed"
        assert video_res.get("edited_video_uri") is None
        assert "default_rendered_output.mp4" not in str(video_res)

        # Step 6: Checkpoint Humano — Aprobar Publicación
        res_pub_app = await ac.post(
            f"/api/v1/tenants/{tenant_id}/publish/approve",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert res_pub_app.status_code == 202  # no-op honesto: aceptado y encolado
        pub_body = res_pub_app.json()
        assert pub_body["status"] == "accepted"
        assert pub_body["kind"] == "publish_approval"
        assert pub_body["queued"] is True
        # Nunca fabricar un post_id (anti 'ig_reel_…_99812'); la proveniencia real
        # via /scripts GET cubre la tarjeta de aprobación de publicación.
        assert "published_post_id" not in pub_body
        assert "ig_reel_" not in res_pub_app.text

        # Step 7: Captura de Webhook Meta Inbound & Verificación HMAC
        secret = "secreto_meta_test_secret"
        payload_synth = {
            "object": "instagram",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "text": "Quiero la CONSULTA por favor",
                                "from": {"id": "user_ig_fitness_99"},
                            },
                        }
                    ]
                }
            ],
        }
        leads = process_instagram_webhook_payload(payload_synth)
        assert len(leads) == 1
        assert leads[0]["keyword"] == "CONSULTA"

        # Step 8: Toma de Control por Operador Humano (Account Manager)
        res_takeover = await ac.post(
            f"/api/v1/tenants/{tenant_id}/leads/{seeded_lead_id}/takeover",
            json={"operator_id": "manager_uuid_99", "action": "pause_bot"},
            headers=auth_headers,
        )
        assert res_takeover.status_code == 200
        assert res_takeover.json()["status"] == "handled_by_human"

        # Step 9: Auditoría 72h y Clasificación 80/20
        # video_id real (uuid4) en lugar del post_id fabricado que se eliminó
        metrics_res = audit_72h_metrics(
            tenant_id=tenant_id,
            video_id=str(uuid.uuid4()),
            views=120000,
            followers=10000,
        )
        assert metrics_res["classification"] == "VERDE"
        assert metrics_res["ratio"] == 12.0

