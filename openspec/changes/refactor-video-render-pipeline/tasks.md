# Tareas de Ingeniería: Refactorización de Renderizado y Conexiones del Grafo

- [x] **Configuración de Dependencias:** Fijar `pillow<10.0.0` y `numpy<2.0.0` en `requirements.txt` del microservicio renderer.
- [x] **Tipografía en Contenedor:** Añadir `fonts-dejavu-core` y `fonts-liberation` al `Dockerfile` del renderer.
- [x] **Mapeo de Palabras Clave:** Construir `_keywords_from_prompt` con diccionario temático Español-Inglés.
- [x] **Superposición Fotograma a Fotograma:** Desarrollar `draw_overlay_on_image` e integrarlo vía `fl_image` en MoviePy.
- [x] **Redimensionado Adaptativo 9:16:** Implementar recorte centrado según relación de aspecto previa al escalado.
- [x] **Recorte por Duración del Audio:** Recortar el clip final a la duración real devuelta por la síntesis TTS.
- [x] **Propagación en Grafo y Celery:** Transmitir `product_image_url` desde `nodes/video_edit.py` hacia `video_edit_task.py`.
- [x] **Integridad de Base de Datos:** Actualizar `insert_video` en `daos.py` para sincronización multi-inquilino.
- [x] **Transmisión de Estado SSE:** Inyectar eventos de progreso en tiempo real dentro de `graph_execution.py`.
- [x] **Interfaz de Usuario Frontend:** Actualizar componentes `MediaGalleryView`, `ScriptInspectorView`, `IdeaApprovalView` y `ProductIngestModal`.
