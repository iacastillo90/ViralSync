# Especificación del Diccionario de Mapeo Semántico (Español -> Inglés)

## Motivación
La API de Pexels entrega mejores resultados de video cuando las consultas se realizan con términos específicos en inglés en lugar de descripciones de prompts en español traducidas literalmente.

## Tabla de Mapeo Directo

| Término en Español | Palabras Clave en Inglés (Pexels Search) |
|---|---|
| micrófono / audio / podcast | `["microphone", "podcast", "studio audio"]` |
| audífonos / música / sonido | `["headphones", "listening music", "studio audio"]` |
| cámara / foto / video | `["camera lens", "filmmaking", "photographer"]` |
| teléfono / celular / smartphone | `["smartphone", "using phone", "mobile app"]` |
| laptop / computadora / pc | `["laptop typing", "desk workspace", "technology"]` |
| luz / iluminación / rgb | `["rgb lighting", "neon lights", "studio setup"]` |
| producto / unboxing / marca | `["product showcase", "unboxing", "minimalist desk"]` |

## Algoritmo de Extracción
1. Tokenizar la entrada combinada (prompt visual + título + texto de la escena).
2. Filtrar palabras de paro (stop words en español).
3. Buscar coincidencias en la tabla de mapeo.
4. Retornar hasta 3 términos de alta relevancia en inglés.
