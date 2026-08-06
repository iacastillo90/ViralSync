"""
filter_5_50.py

Filtro binario previo 5/50 (Gate de Descarte Temprano).
Evaluación rápida antes de calcular RUM:
1. ¿Lo entendería un niño de 5 años? (entendible_nino_5_anos)
2. ¿Le interesaría a 50 de cada 100 personas tomadas al azar? (interesa_50_de_100)
"""

from typing import Dict, Any


def passes_5_50_filter(idea: Dict[str, Any]) -> bool:
    """
    Retorna True si la idea aprueba ambas preguntas binarias.
    Retorna False si cualquiera de las dos es False o está ausente.
    """
    entendible = bool(idea.get("entendible_nino_5_anos", False))
    interesante = bool(idea.get("interesa_50_de_100", False))
    return entendible and interesante
