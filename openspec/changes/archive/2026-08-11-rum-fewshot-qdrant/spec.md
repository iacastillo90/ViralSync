# OpenSpec Spec: RUM Few-Shot Learning Loop en Qdrant

## Requirements & Scenarios

### REQ-RFL-01: Extracción e Indexación 80/20 de Videos Exitosos
- **Scenario 1:** La tarea `run_rum_learning_task` selecciona los videos con mayores tasas de retención/conversión a 72h para un tenant e indexa sus guiones en Qdrant.

### REQ-RFL-02: Recuperación RUM en Agente de Ideación
- **Scenario 1:** Al ejecutar `node_ideation`, el nodo consulta la colección `rum_golden_examples` en Qdrant y recupera hasta 3 ejemplos Few-Shot contextuales.
- **Scenario 2:** En ausencia de Qdrant o colección vacía (fallback), el prompt de ideación continúa funcionando con los defaults de RUM sin interrumpir el flujo.
