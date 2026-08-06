# 📄 TESTING_STRATEGY.md — Estrategia de Pruebas, Mocks & TDD en ViralSync

## 🎯 Visión General
Esta guía especifica la **estrategia de pruebas automatizadas (TDD/BDD)** para el backend de ViralSync. Garantiza que el desarrollo de agentes, webhooks y tareas asíncronas se realice sin gastar tokens de APIs pagadas, sin depender de cuentas de Instagram activas durante las pruebas locales y asegurando la estabilidad del sistema en `AGENCY_ENV=dev`.

---

## 🛡️ 1. Filosofía de Pruebas & Ahorro de Tokens

1. **Cero Gasto de Tokens en Testing:** Toda la suite de pruebas unitarias e integración se ejecuta utilizando modelos locales vía **Ollama** (`AGENCY_ENV=dev`) o **mocks deterministas en Python** que simulan respuestas JSON estáticas de LiteLLM Proxy.
2. **Entorno Aislado de Webhooks:** La captura de DMs y comentarios se prueba localmente con payloads sintéticos firmados con HMAC SHA-256 o exponiendo el puerto 8000 mediante `ngrok`.

---

## 🎭 2. Simulación y Mocking de LiteLLM Proxy

Para probar la lógica del grafo LangGraph o el filtrado RUM sin llamar a LLMs externos, se sustituyen las respuestas HTTP de `http://localhost:4000/v1` por respuestas estáticas estructuradas.

### 2.1 Fixture pytest para Mockear LiteLLM
```python
# tests/fixtures/mock_litellm.py
import pytest
from unittest.mock import patch

MOCK_IDEATION_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": """[
                    {
                        "texto": "3 Errores en Negocios B2B",
                        "gancho": "Si trabajas en B2B...",
                        "entendible_nino_5_anos": true,
                        "interesa_50_de_100": true,
                        "universalidad": 0.85,
                        "intensidad": 0.90,
                        "claridad": 0.95,
                        "shareability": 0.80,
                        "distribucion": 0.85,
                        "alineacion": 0.90
                    }
                ]"""
            }
        }
    ]
}

@pytest.fixture
def mock_litellm_proxy():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = MOCK_IDEATION_RESPONSE
        yield mock_post
```

---

## 🌐 3. Exposición Local para Webhooks Meta (`ngrok` / `localtunnel`)

Para probar la recepción de eventos reales de Instagram Graph API en tu entorno local sin desplegar en producción:

### 3.1 Uso de `ngrok`
```bash
# Exponer el puerto 8000 de FastAPI
ngrok http 8000
```

Copia la URL pública HTTPS generada por ngrok (ej: `https://a1b2c3.ngrok-free.app`) y configúrala en el panel de desarrolladores de Meta Meta App Dashboard:
- **Callback URL:** `https://a1b2c3.ngrok-free.app/webhooks/instagram`
- **Verify Token:** El valor de `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` definido en tu `.env`.

---

### 3.2 Script para Simular Webhook Sintético con Firma HMAC SHA-256
No necesitas esperar un DM real en Instagram para probar el calificador de leads. Puedes ejecutar este script local que genera la firma `X-Hub-Signature-256` requerida por `instagram_inbound.py`:

```python
# tests/scripts/send_synthetic_webhook.py
import hmac
import hashlib
import json
import httpx

APP_SECRET = "mi_secreto_meta_local"
TARGET_URL = "http://localhost:8000/webhooks/instagram"

payload = {
    "object": "instagram",
    "entry": [
        {
            "id": "178414000000000",
            "time": 1722900000,
            "changes": [
                {
                    "field": "comments",
                    "value": {
                        "id": "comment_99812",
                        "text": "Quiero la CONSULTA por favor",
                        "from": {"id": "user_ig_9921", "username": "cliente_demo"}
                    }
                }
            ]
        }
    ]
}

payload_bytes = json.dumps(payload).encode("utf-8")
signature = hmac.new(APP_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={signature}"
}

response = httpx.post(TARGET_URL, content=payload_bytes, headers=headers)
print(f"Status: {response.status_code}, Body: {response.json()}")
```

---

## 📁 4. Estructura Completa de Tests en `pytest`

```
agency/tests/
├── conftest.py                 # Fixtures globales (DB PostgreSQL temporal, Qdrant Mock, LiteLLM Mock)
├── unit/                       # Pruebas Unitarias Rápidas
│   ├── test_rum_calculator.py  # Prueba de la fórmula RUM U*I*C*S*D*A
│   ├── test_filter_5_50.py     # Prueba del gate binario
│   ├── test_lead_qualifier.py  # Prueba del calificador ligero de DMs
│   └── test_sse_manager.py     # Prueba de difusión de eventos SSE
├── integration/                # Pruebas de Integración con Infraestructura
│   ├── test_graph_execution.py # Prueba del StateGraph LangGraph con PostgresSaver
│   ├── test_fastapi_endpoints.py # Prueba de clientes httpx contra FastAPI main.py
│   ├── test_webhooks_hmac.py   # Prueba de firmas válidas e inválidas en Meta webhook
│   └── test_celery_tasks.py    # Prueba de video_edit_task y metrics_loop_task
└── e2e/                        # Pruebas de Flujo Completo
    └── test_full_pipeline.py   # Ingesta -> Ideación -> Checkpoint -> Guion -> Pub
```

---

## 🚀 5. Comandos para Ejecutar las Pruebas

```bash
# Ejecutar toda la suite de pruebas en entorno dev
AGENCY_ENV=dev pytest agency/tests/

# Ejecutar solo pruebas unitarias con reporte de cobertura
AGENCY_ENV=dev pytest agency/tests/unit/ --cov=agency/agents --cov=agency/backend

# Ejecutar pruebas de integración de webhooks Meta HMAC
AGENCY_ENV=dev pytest agency/tests/integration/test_webhooks_hmac.py
```
