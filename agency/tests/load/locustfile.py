"""
locustfile.py

Arnés de Pruebas de Carga Sostenida y Soak Testing con Locust para ViralSync.
Simula tráfico concurrente de usuarios consumiendo la API REST, eventos SSE y webhooks inbound.
"""

from locust import HttpUser, task, between

# Piscina de tenants de prueba para repartir la carga (REQ-LLT-01): simular
# tráfico concurrente multi-tenant en vez de golpear siempre a default_tenant.
TENANT_IDS = [f"tenant_loadtest_{i}" for i in range(1, 11)]


class ViralSyncTenantUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_health(self):
        """Verificación de probes de salud de FastAPI."""
        self.client.get("/health")

    @task(2)
    def fetch_ideas(self):
        """Lectura de ideas del tenant (endpoint real GET /ideas)."""
        tenant = TENANT_IDS[self.environment.runner.user_count % len(TENANT_IDS)]
        self.client.get(f"/api/v1/tenants/{tenant}/ideas")

    @task(1)
    def trigger_graph_run(self):
        """Disparo de campaña de IA (endpoint real POST /graph/run)."""
        tenant = TENANT_IDS[self.environment.runner.user_count % len(TENANT_IDS)]
        self.client.post(
            f"/api/v1/tenants/{tenant}/graph/run",
            json={"product_name": "Microfono USB profesional", "duration": 30},
        )

    @task(1)
    def post_webhook_lead(self):
        """Simulación de captura de lead inbound."""
        payload = {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "user_locust_test"},
                            "message": {"text": "Quiero la CONSULTA de negocio"},
                        }
                    ]
                }
            ]
        }
        self.client.post("/api/v1/webhooks/instagram", json=payload)
