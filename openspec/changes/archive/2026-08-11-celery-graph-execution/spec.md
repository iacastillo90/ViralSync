# OpenSpec Spec: Celery Graph Execution

## Requirements & Scenarios

### REQ-CGE-01: Ejecución Asíncrona Duradera en Celery
- **Scenario 1:** Cuando un cliente invoca `POST /graph/run`, el router encola la tarea `run_graph_task.delay(tenant_id, initial_state)` en Celery.
- **Scenario 2:** La tarea Celery ejecuta la corrutina `_run_graph_background(tenant_id, initial_state)` mediante `asyncio.run()`.
- **Scenario 3:** Si la ejecución del grafo falla con una excepción unhandled, Celery captura el error, registra los detalles y emite el evento SSE `graph_error` estructurado.

### REQ-CGE-02: Reanudación de Grafo vía Celery
- **Scenario 1:** Cuando se aprueba una idea o publicación en `/ideas/approve` o `/publish/approve`, el router encola `resume_graph_task.delay(tenant_id, update_dict)`.
- **Scenario 2:** El checkpointer de PostgreSQL recupera el estado guardado y reanuda el grafo desde la interrupción `human_approval`.

### REQ-CGE-03: Compatibilidad Eager y Fallback en Testing
- **Scenario 1:** Cuando `CELERY_TASK_ALWAYS_EAGER=true` está activo (en pruebas unitarias pytest), Celery ejecuta la tarea de forma síncrona manteniendo la velocidad del arnés de pruebas.
