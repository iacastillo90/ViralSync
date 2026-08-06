# Fórmula RUM (Relevancia Universal de Mercado)

## Principio
Un contenido se vuelve viral cuando cruza el umbral de relevancia mínima de su nicho — no antes, sin importar cuánto valor aporte objetivamente. El umbral no es una constante universal: sube o baja según qué tan bueno sea, en promedio, el contenido que ya se publica en ese nicho.

## Fórmula
```
RUM = U × I × C × S × D × A
```

## Variables (Puntuación de 0.0 a 1.0)
- **U — Universalidad:** Qué porcentaje de personas, sin contexto previo, entendería y se interesaría en el contenido.
- **I — Intensidad:** Cuánto duele el problema o cuánto se desea el resultado que se promete.
- **C — Claridad:** Si se entiende a la primera exposición, sin necesidad de releer o repetir.
- **S — Shareability:** Si alguien lo reenviaría aunque no sea el comprador potencial.
- **D — Distribución:** Si le interesaría incluso a alguien que jamás comprará (esas personas son las que lo empujan hacia audiencias nuevas).
- **A — Alineación:** Si el cierre del contenido conecta específicamente con el cliente ideal real del negocio.

## Umbral Dinámico
El umbral de descarte se calcula dinámicamente como un percentil (ejemplo: percentil 70) sobre el histórico de RUM del propio nicho en la tabla `rum_thresholds` — **nunca** como un número fijo hardcodeado en el código.
