# Diagrama de Arquitectura del Pipeline de Renderizado 9:16

```mermaid
graph TD
    User[Frontend Next.js] -->|POST /graph/run| Router[backend/routers/graph_execution.py]
    Router -->|Trigger| Graph[agency/agents/graph.py]
    Graph -->|Node Video Edit| NodeEdit[agency/agents/nodes/video_edit.py]
    NodeEdit -->|Presign Product Image| MinIOClient[agency/backend/storage/minio_client.py]
    NodeEdit -->|Celery Task| Worker[agency/workers/video_edit_task.py]
    Worker -->|HTTP POST /render| Renderer[agency/microservices/renderer/app.py]
    Renderer -->|Download Stock Video| Pexels[API Pexels]
    Renderer -->|Fetch Presigned Image (Host header)| MinIODocker[MinIO S3 Container]
    Renderer -->|MoviePy Overlay Compositing| RenderEngine[draw_overlay_on_image]
    Renderer -->|Upload Reel MP4| MinIODocker
    Worker -->|Insert DB Video DAO| Postgres[(PostgreSQL DB)]
    Router -->|SSE Stream Events| User
```

## Descripción del Flujo
1. **Frontend:** Inicia la generación con el nombre del producto y metadatos.
2. **Grafo de Agentes:** El nodo de edición prepara las URLs presignadas.
3. **Worker Celery:** Dispara la renderización asíncrona hacia el microservicio.
4. **Renderer FastAPI:** Realiza la composición visual 9:16 y sube el archivo resultante a MinIO.
