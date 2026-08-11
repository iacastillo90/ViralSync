# OpenSpec Proposal: RUM Few-Shot Learning Loop en Qdrant

- **Change ID:** `rum-fewshot-qdrant`
- **Scope:** Worker Celery para aprendizaje automático 80/20 sobre métricas a 72h e inyección dinámica de ejemplos *Golden Few-Shot* en los prompts del agente de ideación RUM.

## Problem Statement
Las métricas post-publicación a 72h de los videos se almacenan en la tabla `videos` (`migrations/002_add_video_metrics_and_fix_leads.sql`), pero actualmente no existe un mecanismo de aprendizaje continuo que retroalimente a los agentes. El agente de ideación genera guiones sin utilizar la evidencia empírica de qué ganchos/estructuras funcionaron mejor para cada tenant.

## Proposed Solution
1. **Worker Task (`workers/rum_learning_task.py`):**
   - Tarea periódica Celery que extrae el 20% superior de videos con mejores métricas por tenant/nicho, formatea sus guiones/hooks e indexa sus embeddings en Qdrant en la colección `rum_golden_examples`.
2. **Inyección en Ideación (`agents/nodes/ideation.py` / `prompt_context.py`):**
   - Consultar ejemplos vectoriales similares desde Qdrant antes de construir el prompt del LLM, inyectando los *Golden Few-Shot Examples* reales como contexto para guiar la generación de nuevas ideas.
