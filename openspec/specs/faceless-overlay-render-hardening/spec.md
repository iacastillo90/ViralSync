# Specification: Faceless Overlay Render & Pipeline Hardening

## Purpose

Este documento define la especificación técnica para la composición visual de videos verticales 9:16 en el microservicio faceless `video_renderer`, la gestión de firmas presignadas en MinIO bajo arquitectura multi-inquilino (multi-tenant), y el flujo de datos punta a punta desde los agentes de LangGraph hasta los workers de Celery.

## Contexto & Decisiones de Diseño

### Decision 1: Composición Nativa de Superposiciones (Overlays) en MoviePy/PIL
**Motivación:** En iteraciones anteriores, los clips de video descargados desde Pexels se presentaban sin elementos superpuestos o provocaban recuadros negros en el tercio inferior debido al uso de fondos oscuros opacos y operaciones `crop()` defectuosas.
**Solución:** Se implementa `draw_overlay_on_image()`, que integra:
1. **Tarjeta Flotante de Producto (Tercio Superior):** Renderiza la imagen del producto sobre una tarjeta semitransparente con borde dorado y curva suave de respiración (animación Ken Burns).
2. **Subtítulos Glassmorphic (Tercio Inferior):** Badge oscuro con 85% de opacidad y borde dorado, con tipografía Truetype en negrita (`DejaVuSans-Bold.ttf`) que resalta la primera línea en amarillo `#FACB15` y el cuerpo en blanco `#FFFFFF`.

### Decision 2: Preservación de Firmas AWS SigV4 y Cabecera Host en Entornos Docker
**Motivación:** Al descargar imágenes presignadas desde MinIO dentro de la red interna de Docker (`http://minio:9000`), la firma de URL calculada contra el host externo devolvía errores HTTP 403 Forbidden.
**Solución:** Se inyecta la cabecera HTTP `Host: localhost:9000` en el cliente `requests`, garantizando que la validación del hash HMAC-SHA256 SigV4 coincida exactamente sin alterar la seguridad del bucket privado.

### Decision 3: Mapeo Temático de Palabras Clave para Pexels API
**Motivación:** Las búsquedas en la API de Pexels usando promps genéricos devolvían b-roll irrelevante (edificios o personas en oficinas).
**Solución:** Se establece un diccionario semántico en `_keywords_from_prompt` que mapea menciones de producto (ej. "micrófono", "fifine k688", "audio") a términos en inglés de alta resolución como `["microphone", "podcast", "studio audio"]`.

### Decision 4: Aislamiento de Dependencias de Renderizado (`pillow < 10.0.0`)
**Motivación:** `MoviePy 1.0.3` utiliza la constante obsoleta `PIL.Image.ANTIALIAS`, la cual fue removida en Pillow 10+, causando excepciones fatales en tiempo de ejecución.
**Solución:** Se fijó `pillow<10.0.0` y `numpy<2.0.0` en `requirements.txt` del contenedor y se aplicó un monkey-patch preventivo en la raíz de `app.py`.

---

## Requerimientos

### REQ-FOR-01: Inyección de `product_image_url` en el Grafo de Edición
El sistema DEBE propagar la URL presignada de la imagen del producto desde el nodo `node_video_edit` hacia Celery `trigger_video_render` y el microservicio `video_renderer`.

### REQ-FOR-02: Renderizado Continuo con Fallback Animado
Si la API de Pexels no retorna clips o falla la conexión a internet, el sistema DEBE generar una escena animada vectorial pura utilizando gradientes índigo y la imagen de producto en alta resolución.

### REQ-FOR-03: Sincronización Estricta de Duración (15s, 30s, 45s, 60s)
El video final DEBE tener una duración total de exactamente 15.0s, 30.0s, 45.0s o 60.0s, ajustando la velocidad del audio TTS y de los clips de video para coincidir con la duración estricta seleccionada.

### REQ-FOR-04: Subtítulos Dinámicos Estilo Karaoke
El motor de renderizado DEBE destacar la palabra activa siendo pronunciada en tiempo real en amarillo brillante `#FACB15` con contorno negro de 4px, manteniendo palabras previas en blanco y palabras futuras en blanco tenue, sobre un contenedor glassmorphism en el tercio inferior.

### REQ-FOR-05: Fondos B-roll Transicionales Dinámicos
El sistema DEBE extraer keywords de búsqueda en inglés basadas dinámicamente en el producto/servicio registrado en el formulario (SaaS, audio, fitness, inmobiliaria, restaurantes, etc.) y rotar múltiples shorts verticales de Pexels con transiciones rápidas cada 2.5–3 segundos.
