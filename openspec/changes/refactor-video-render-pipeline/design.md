# Documento de Diseño: Composición Visual y Firma de URLs Multi-Tenant

## Arquitectura del Microservicio Renderer (`agency/microservices/renderer`)

### 1. Parche de Compatibilidad PIL / MoviePy
MoviePy 1.0.3 invoca internamente `PIL.Image.ANTIALIAS`, atributo que fue removido en Pillow 10+. Para prevenir la interrupción del pipeline durante la manipulación de imágenes, se aplica un monkey-patch global al iniciar la aplicación FastAPI:
```python
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
```

### 2. Motor de Superposición Visual (`draw_overlay_on_image`)
Para lograr una estética de alto impacto sin requerir motores pesados de edición:
- **Tarjeta de Producto (Tercio Superior):** Dibujada sobre una superficie semitransparente (`rgba(15, 23, 42, 220)`) con bordes redondeados y contorno dorado (`#EAB308`). Integra la imagen del producto escalada y centrada.
- **Subtítulos Glassmorphic (Tercio Inferior):** Badge centrado con tipografía TrueType escalable (`DejaVuSans-Bold.ttf`). Resalta la primera palabra del texto en amarillo brillante (`#FACB15`) y el cuerpo en blanco puro (`#FFFFFF`).

### 3. Validación de Firmas AWS SigV4 en Red Interna Docker
Cuando el renderer descarga la imagen de producto desde MinIO usando la URL presignada por el backend (`http://localhost:9000/...`), la petición HTTP originada dentro del contenedor se redirige a `http://minio:9000/...`. Para evitar que la alteración del hostname rompa la firma HMAC-SHA256, se inyecta explícitamente la cabecera:
```python
headers = {"Host": "localhost:9000"} if "minio:9000" in fetch_url else {}
```

### 4. Estrategia de Fallback Animado Vectorial
Si la consulta a Pexels API no arroja resultados para las palabras clave derivadas del prompt, se utiliza `VideoClip` para generar un video animado procedural en tiempo de ejecución, combinando el fondo de marca con las tarjetas visuales de producto e información.
