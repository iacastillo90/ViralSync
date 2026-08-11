# OpenSpec Proposal: SSE Redis Pub/Sub Multi-Replica & Frontend Consumer (RES-002)

- **Change ID:** `sse-redis-pubsub`
- **Scope:** Habilitar el suscriptor Redis Pub/Sub en `sse_manager.py` para sincronizar eventos entre réplicas del backend y actualizar la interfaz React para manejar eventos de rechazo/error terminal.

## Problem Statement
1. **Multi-replica SSE Desincronizado:** `sse_manager.py` actualmente publica eventos a `redis.publish(f"sse:{tenant_id}", ...)` pero ninguna réplica backend escucha ese canal. Si el backend escala a 2 o más pods, los eventos emitidos en una réplica no llegan a los clientes conectados a otra réplica.
2. **Frontend Pausado en Rechazos (RES-002):** Cuando el grafo termina en estado de rechazo (`term_rejected`) o emite `graph_error` con código de error, el componente frontend no captura adecuadamente estos eventos terminales, dejando los indicadores de progreso en un estado animado o "pausado" indefinido.

## Proposed Solution
1. **Backend:** Agregar un listener asíncrono en `sse_manager.py` que realice `pubsub.subscribe(f"sse:{tenant_id}")` cuando se conecta un cliente y retransmita los mensajes a las colas locales `_listeners`.
2. **Frontend:** Actualizar `ExecutionTracker.tsx` para interceptar los eventos SSE `graph_complete`, `term_rejected` y `graph_error`, limpiando spinners y mostrando la alerta correspondiente.
