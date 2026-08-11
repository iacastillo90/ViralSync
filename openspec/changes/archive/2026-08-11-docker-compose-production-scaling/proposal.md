# OpenSpec Proposal: Docker Compose Production Multi-Worker Scaling

- **Change ID:** `docker-compose-production-scaling`
- **Scope:** Creación de `agency/docker-compose.production.yml` configurando la segregación de workers Celery por especialidad (`rendering`, `webhooks`, `default`), límites de memoria/CPU, y healthchecks para resiliencia productiva.

## Problem Statement
Actualmente el despliegue con Celery utiliza una sola cola genérica o falta un archivo de composición de producción explícito donde se limite el consumo de memoria del worker de renderizado (video rendering) para prevenir desbordamientos OOM sobre el API backend principal.

## Proposed Solution
1. Crear `agency/docker-compose.production.yml`.
2. Segregar los workers de Celery en 3 servicios:
   - `celery_rendering`: `-Q rendering` con asignación de recursos dedicada.
   - `celery_webhooks`: `-Q webhooks` para procesamiento de webhooks Meta/Instagram.
   - `celery_default`: `-Q default` escalable a múltiples réplicas.
3. Definir healthchecks explícitos y políticas de reinicio `restart: always`.
