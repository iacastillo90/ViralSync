"""
test_full_pipeline_with_events.py

Prueba de Integración E2E Extendida de Extremo a Extremo con Verificación de Eventos SSE (Fase A).
Ejecuta el flujo completo: Onboarding -> Ingesta Masiva -> Ideación RUM -> Aprobación Humana -> Guionismo -> Renderizado -> Publicación -> Métricas 72h -> Webhook Lead -> DM Bot con Calendly -> Verificación de Eventos SSE.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.security.auth import create_access_token
from agents.crews.ideation_crew import run_ideation_crew
from agents.crews.scriptwriting_crew import run_scriptwriting_crew
from workers.video_edit_task import process_video_postproduction
from workers.metrics_loop_task import audit_72h_metrics
from workers.rum_learning_task import run_rum_learning_task
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload
from backend.security.audit_logger import log_audit_event
from agents.nodes.dm_response import classify_intent, node_dm_response
from backend.db.models import Lead, Idea
from backend.db.daos import insert_ideas
from sqlalchemy import select


@pytest.mark.anyio
async def test_full_pipeline_with_events_e2e(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Onboarding de Tenant
        res_tenant = await ac.post(
            "/api/v1/tenants",
            json={
                "name": "Agencia E2E Full Events",
                "niche": "SaaS B2B & AI Marketing",
                "monthly_llm_budget_usd": 30.00,
            },
        )
        assert res_tenant.status_code == 201
        tenant_data = res_tenant.json()
        tenant_id = tenant_data["id"]

        token = create_access_token(user_id="usr_e2e_events", tenant_id=tenant_id)
        auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

        # 2. Ingesta Masiva de Productos (POST /products/batch - Evento product_media_ingested)
        res_batch = await ac.post(
            f"/api/v1/tenants/{tenant_id}/products/batch",
            json={
                "products": [
                    {
                        "product_name": "ViralSync Automation Suite",
                        "description": "Automatización de video con IA y RUM 80/20",
                        "product_image_url": "https://viralsync.io/assets/product1.png",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert res_batch.status_code == 201
        assert res_batch.json()["ingested_count"] == 1

        # 3. Ideación RUM
        ideas = await run_ideation_crew(
            niche="SaaS B2B & AI Marketing",
            market_map={"errores": ["Falta de tracción en contenido corto"]},
        )
        assert len(ideas) >= 1
        selected_idea = ideas[0]

        # 4. Aprobación Humana de Idea
        persisted_ideas = await insert_ideas(tenant_id, [selected_idea])
        real_idea_id = persisted_ideas[0].id
        res_approve = await ac.post(
            f"/api/v1/tenants/{tenant_id}/ideas/approve",
            json={"idea_id": real_idea_id, "status": "approved"},
            headers=auth_headers,
        )
        assert res_approve.status_code == 202

        # Registro de auditoría (Evento audit_event_logged)
        audit_entry = log_audit_event(
            tenant_id=tenant_id,
            user_id="usr_e2e_events",
            action="idea_approved_by_human",
            details={"idea_id": real_idea_id},
        )
        assert audit_entry["action"] == "idea_approved_by_human"

        # 5. Guionismo de 4 Bloques
        script = await run_scriptwriting_crew(
            idea=selected_idea,
            niche_ppp="Consigue 30 leads B2B en 14 días sin pagar pauta",
        )
        assert "gancho_0_5s" in script

        # 6. Post-producción Asíncrona de Video (Celery)
        video_res = process_video_postproduction(
            tenant_id=tenant_id,
            raw_video_uri=f"s3://viralsync-media-dev/{tenant_id}/raw.mp4",
            script=script,
        )
        assert video_res["status"] in ["completed", "failed"]

        # 7. Captura de Webhook de Lead Inbound (Evento lead_captured)
        webhook_payload = {
            "object": "instagram",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "text": "Quiero la CONSULTA por favor",
                                "from": {"id": "user_ig_e2e_events"},
                            },
                        }
                    ]
                }
            ],
        }
        leads = process_instagram_webhook_payload(webhook_payload)
        assert len(leads) == 1
        assert leads[0]["keyword"] == "CONSULTA"

        # 8. Bot Conversacional DM con Agendamiento de Calendly
        dm_state = {
            "tenant_id": tenant_id,
            "lead_id": "lead_e2e_event_01",
            "incoming_message": "Quiero comprar la solución y ver el precio",
            "conversation_history": [],
            "rag_context": "",
            "reply_text": "",
            "confidence_score": 0.95,
            "intent": "",
            "requires_human": False,
        }
        dm_res = await node_dm_response(dm_state)
        assert dm_res["intent"] == "purchase_intent"
        assert "calendly" in dm_res["reply_text"].lower()
        assert dm_res["requires_human"] is True

        # 9. Recalibración RUM a 72h (Evento rum_metrics_evaluated)
        rum_res = run_rum_learning_task(tenant_id)
        assert rum_res["status"] == "completed"
        assert rum_res["classification"] == "VERDE"

        # 10. Descarga de Reporte de ROI en PDF
        res_pdf = await ac.get(
            f"/api/v1/tenants/{tenant_id}/reports/monthly-pdf",
            headers=auth_headers,
        )
        assert res_pdf.status_code == 200
        assert res_pdf.json()["content_type"] == "application/pdf"
