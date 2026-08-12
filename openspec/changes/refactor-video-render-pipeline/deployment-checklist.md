# Lista de Verificación para Despliegue en Producción

- [x] **Variables de Entorno:** Verificar `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `POSTGRES_URI` y `REDIS_URL`.
- [x] **Construcción de Imágenes Docker:** Reconstruir la imagen `renderer` asegurando la instalación de fuentes tipográficas y dependencias fijas (`pillow<10.0.0`).
- [x] **Verificación de Buckets:** Confirmar la existencia del bucket `agency-media` en MinIO con políticas privadas.
- [x] **Migraciones de Base de Datos:** Ejecutar `alembic upgrade head` para asegurar la tabla de videos y tenants.
- [x] **Pruebas de Humo:** Disparar un video de prueba desde la interfaz de administración y verificar la reproducción vertical.
