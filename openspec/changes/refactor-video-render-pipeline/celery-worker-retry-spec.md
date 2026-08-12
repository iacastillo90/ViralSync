# Especificación de Reintentos y Manejo de Errores en Celery Workers

## Política de Reporte Transparente
- **Prohibición de URIs Falsas:** Bajo ninguna circunstancia el worker `video_edit_task` debe fabricar una URL ficticia en S3 cuando falle la renderización.
- **Manejo de Excepciones:** Si el microservicio renderer retorna un código de estado `5xx` o agota el tiempo de espera (timeout), la tarea debe fallar limpiamente registrando el error en los logs de Celery.
- **Actualización de Estado en DB:** Actualizar el registro del video con estado `failed` y almacenar el mensaje de error técnico para inspección en la vista de monitoreo.
