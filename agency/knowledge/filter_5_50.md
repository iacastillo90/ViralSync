# Filtro 5/50 (Gate Previo)

## Principio
Antes de gastar tokens en el scoring RUM completo, cada idea pasa por dos preguntas binarias de evaluación rápida:

1. **¿Lo entendería un niño de 5 años?** (`entendible_nino_5_anos`)
2. **¿Le interesaría a al menos 50 de cada 100 personas tomadas al azar en la calle?** (`interesa_50_de_100`)

## Regla de Descarte
Si cualquiera de las dos respuestas es "no" (`False`), la idea se descarta de inmediato sin calcular el RUM score. Esta optimización elimina conceptos excesivamente complejos o ultra-nichados antes de consumir computación en el scoring multi-variable.
