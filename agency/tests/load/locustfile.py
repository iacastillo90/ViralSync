"""
locustfile.py

Script de pruebas de carga Locust para simular tráfico masivo de tenants (REQ-LLT-01/02).
Simula usuarios navegando el dashboard, consultando salud, enviando ejecuciones de grafo y comprobando la protección por rate limiting (HTTP 429).
"""

try:
    from locust import HttpUser, task, between
except ImportError:
    class HttpUser: pass
    def task(weight=1): return lambda f: f
    def between(a, b): return lambda: a

TENANT_IDS = [f"tenant_loadtest_{i}" for i in range(1, 20)]



class ViralSyncTenantUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Asigna un tenant_id dinámico al usuario Locust."""
        self.tenant_id = random.choice(TENANT_IDS)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer mock_jwt_{self.tenant_id}",
        }

    @task(5)
    def check_health(self):
        """Consulta el estado de salud del sistema."""
        self.client.get("/api/v1/health", name="/health")

    @task(3)
    def fetch_ideas(self):
        """Consulta las ideas creadas para el tenant."""
        self.client.get(
            f"/api/v1/tenants/{self.tenant_id}/ideas",
            headers=self.headers,
            name="/tenants/{tenant_id}/ideas",
        )

    @task(2)
    def trigger_graph_run(self):
        """Envía una solicitud de ejecución de grafo."""
        payload = {
            "ig_access_token": "valid_token_loadtest_sample",
            "ig_user_id": "178414000000000",
            "niche": "Tecnología B2B",
            "mock_execution": True,
        }
        with self.client.post(
            f"/api/v1/tenants/{self.tenant_id}/graph/run",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/tenants/{tenant_id}/graph/run",
        ) as response:
            # HTTP 200, 202 y 429 son comportamientos válidos bajo carga excesiva
            if response.status_code in [200, 202, 429]:
                response.success()
            else:
                response.failure(f"Código inesperado: {response.status_code}")
