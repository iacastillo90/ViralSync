# OpenSpec Spec: Docker Compose Production Multi-Worker Scaling

## Requirements & Scenarios

### REQ-DCS-01: Segregación Multi-Worker Celery en Docker Compose
- **Scenario 1:** El archivo `docker-compose.production.yml` define explícitamente tres servicios Celery independientes con colas `-Q rendering`, `-Q webhooks` y `-Q default`.
- **Scenario 2:** Cada servicio worker especifica políticas de reinicio `restart: always` y dependencias saludables sobre Redis y PostgreSQL.
