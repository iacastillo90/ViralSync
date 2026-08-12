# Especificación del Reproductor Vertical 9:16 en Frontend

## Características del Reproductor (`MediaGalleryView`)
- Aspect ratio forzado 9:16 con marco estilizado de smartphone.
- Overlay interactivo que simula la vista previa de redes sociales (botones de me gusta, comentarios y subtítulos).
- **Mecanismo de Re-Firmado Dinámico:** Si la URL presignada del video expira (HTTP 403 / 401), la vista solicita automáticamente una nueva URL al backend mediante `GET /api/v1/media/{video_id}/presign` sin refrescar la página.
