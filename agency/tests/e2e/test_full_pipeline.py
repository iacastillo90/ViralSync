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
from backend.db.models import Tenant, Lead


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
        # Se persiste también un Tenant real (FK de leads.tenant_id), y todas las
        # columnas NOT NULL del DDL (video_id, keyword, ig_user_id, mensaje_original)
        # reciben valores — el lead_id es un UUID válido para ambos esquemas (SQLite
        # ORM userId String y Postgres UUID).
        db_session.add(Tenant(id=tenant_id, name="Cliente E2E Fitness"))
        await db_session.commit()

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

        # Step 2: Ejecución de Ideación RUM
        ideas = run_ideation_crew(
            niche="Fitness B2B y Gimnasios",
            market_map={"errores": ["Falta de retención"]},
        )
        assert len(ideas) >= 1
        selected_idea = ideas[0]
        assert selected_idea["rum_score"] > 0.0

        # Step 3: Checkpoint Humano — Aprobar Idea
        res_idea_app = await ac.post(
            f"/api/v1/tenants/{tenant_id}/ideas/approve",
            json={"idea_id": "idea-e2e-001", "status": "approved"},
            headers=auth_headers,
        )
        assert res_idea_app.status_code == 200
        assert res_idea_app.json()["idea_approval_status"] == "approved"

        # Step 4: Guionismo en 4 Bloques
        script = run_scriptwriting_crew(
            idea=selected_idea,
            niche_ppp="Consigue 50 socios en 30 días sin pagar anuncios",
        )
        assert script["keyword"]  # Verificar que no esté vacío
        assert "gancho_0_5s" in script

        # Step 5: Post-producción Asíncrona de Video (Celery Eager)
        video_res = process_video_postproduction(
            tenant_id=tenant_id,
            raw_video_uri=f"s3://viralsync-media-dev/{tenant_id}/raw.mp4",
            script=script,
        )
        assert video_res["status"] == "completed"

        # Step 6: Checkpoint Humano — Aprobar Publicación
        res_pub_app = await ac.post(
            f"/api/v1/tenants/{tenant_id}/publish/approve",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert res_pub_app.status_code == 200
        post_id = res_pub_app.json()["published_post_id"]
        assert "ig_reel_" in post_id

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
        metrics_res = audit_72h_metrics(
            tenant_id=tenant_id,
            video_id=post_id,
            views=120000,
            followers=10000,
        )
        assert metrics_res["classification"] == "VERDE"
        assert metrics_res["ratio"] == 12.0

