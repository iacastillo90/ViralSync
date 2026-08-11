# OpenSpec Proposal: Celery Graph Execution

- **Change ID:** `celery-graph-execution`
- **Scope:** Orquestación de ejecuciones de LangGraph vía Celery en segundo plano en lugar de `BackgroundTasks` de FastAPI.

## Problem Statement
Actualmente los endpoints `/graph/run`, `/ideas/approve` y `/publish/approve` en `agency/backend/routers/graph_execution.py` inician la ejecución asíncrona del grafo utilizando `background_tasks.add_task(...)` de FastAPI. Esto ejecuta las corrutinas en el mismo proceso del servidor web Uvicorn. Si el contenedor del backend se reinicia, sufre un fallo o se despliega una nueva versión mientras un grafo se está ejecutando, la tarea en memoria se interrumpe y nadie la retoma.

## Proposed Solution
1. Crear una tarea de Celery `workers/graph_execution_task.py` con dos funciones decoradas con `@celery_app.task`:
   - `run_graph_task(tenant_id: str, initial_state: dict)`
   - `resume_graph_task(tenant_id: str, config_values: dict)`
2. Registrar `workers.graph_execution_task` en `celery_app.py` bajo la cola `default`.
3. Actualizar `graph_execution.py` para encolar la tarea vía `.delay()` cuando Celery esté disponible o invocar Celery eager mode en testing.
4. Garantizar que ante fallos en Celery task se registre el error y se emita el evento SSE `graph_error`.
