# Especificación del Panel de Administración y Eventos SSE

## Monitoreo en Tiempo Real (`admin/sistema/page.js`)
- Tarjetas de estado con indicadores de salud en vivo para:
  - **Renderer Service:** `http://renderer:8001/health`
  - **MinIO S3:** Estado del bucket y espacio.
  - **PostgreSQL:** Conexión y estado de migraciones Alembic.
  - **Celery / Redis:** Conexión con el broker de mensajes.

## Receptor de Eventos SSE (`PipelineMonitorView`)
- Conexión persistente mediante `EventSource` a `/api/v1/graph/events`.
- Actualización dinámica de barras de progreso y badges con estados (`pending`, `rendering`, `uploaded`, `completed`).
