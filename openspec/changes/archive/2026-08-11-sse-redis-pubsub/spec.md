# OpenSpec Spec: SSE Redis Pub/Sub & Frontend Rejection Handling

## Requirements & Scenarios

### REQ-SRP-01: Retransmisión Pub/Sub Redis Multi-Réplica
- **Scenario 1:** Cuando `sse_manager.publish` publica un evento a `redis.publish(f"sse:{tenant_id}", payload)`, el listener asíncrono en cualquier réplica recibe el mensaje y lo encola en las colas locales `_listeners[tenant_id]`.
- **Scenario 2:** En ausencia de servidor Redis (fallback local), las emisiones continúan funcionando vía colas de memoria locales sin excepción.

### REQ-SRP-02: Manejo de Rechazos y Errores en Frontend (RES-002)
- **Scenario 1:** Al recibir un evento SSE con `terminal: "term_rejected"` o `event: "graph_error"`, el componente frontend detiene las animaciones de carga.
- **Scenario 2:** La UI muestra un banner descriptivo indicando que el contenido fue rechazado o especificando el código de error (`NoCandidatesError`, etc.).
