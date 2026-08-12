# Especificación de Red Interna y Validación AWS SigV4 en Docker

## Problema de Autenticación
Al generar una URL presignada desde el backend (`http://localhost:9000/bucket/key?...`), la firma HMAC-SHA256 incluye el encabezado `Host: localhost:9000`. Cuando el microservicio renderer (que se ejecuta dentro de la red puente de Docker) intenta realizar un `GET` sustituyendo la dirección por `http://minio:9000/...`, el servidor de MinIO rechaza la petición con `HTTP 403 SignatureDoesNotMatch`.

## Solución Técnica Implementada
El cliente de descargas en `app.py` detecta si la URL sustituida utiliza el nombre de servicio interno de Docker y reinyecta explícitamente el encabezado originario:

```python
headers = {}
if "minio:9000" in fetch_url:
    headers["Host"] = "localhost:9000"

response = requests.get(fetch_url, headers=headers, timeout=8.0)
```

## Criterios de Aceptación
- La descarga de objetos presignados debe responder con `HTTP 200 OK` dentro del contenedor.
- No se deben alterar los permisos de acceso público del bucket de MinIO.
