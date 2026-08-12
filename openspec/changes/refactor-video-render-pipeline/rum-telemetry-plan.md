# Plan de Telemetría Real User Monitoring (RUM) y Rendimiento

## Métrica Clave de Desempeño
- **TTFR (Time to First Render):** Tiempo transcurrido desde el disparo en `/graph/run` hasta la disponibilidad de la URL del video en MinIO.
- **Pexels API Latency:** Tiempo consumido en la descarga de clips de stock (Target < 3.5s).
- **TTS Generation Latency:** Tiempo de sintesis de voz por escena (Target < 1.2s).
- **MoviePy Compositing Time:** Tiempo de procesamiento de fotogramas (Target < 8.0s para 30s de video).

## Puntos de Inserción de Eventos
1. **Backend Router:** Log de inicio con `tenant_id` y `session_id`.
2. **Celery Task:** Emisión de evento SSE al iniciar y finalizar la renderización.
3. **Renderer Microservice:** Métrica de memoria consumida durante `write_videofile`.
