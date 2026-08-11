"""
locustfile.py

Arnés de Pruebas de Carga Sostenida y Soak Testing con Locust para ViralSync.
Simula tráfico concurrente de usuarios consumiendo la API REST, eventos SSE y webhooks inbound.
"""

from locust import HttpUser, task, between


class ViralSyncUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_health(self):
        """Verificación de probes de salud de FastAPI."""
        self.client.get("/health")

    @task(2)
    def get_tenant_metrics(self):
        """Lectura de métricas 72h por tenant."""
        self.client.get("/api/v1/tenants/default_tenant/metrics/72h")

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
