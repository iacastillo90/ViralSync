# Tasks: Celery Graph Execution

- [ ] **TCGE-001 (RED)** — Crear suite de pruebas unitarias para validación de ejecución de grafo vía Celery (`agency/tests/unit/test_celery_graph_execution.py`).
- [ ] **TCGE-002 (GREEN)** — Implementar `workers/graph_execution_task.py` e incluirlo en `celery_app.py`.
- [ ] **TCGE-003 (GREEN)** — Actualizar `backend/routers/graph_execution.py` para invocar `.delay()` de las tareas Celery.
- [ ] **TCGE-004 (REFACTOR & VERIFY)** — Ejecutar pruebas unitarias completas y generar el `verify-report.md`.
