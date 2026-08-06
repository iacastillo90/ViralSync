"""
rum_calculator.py

Calculador de la Fórmula RUM (Relevancia Universal de Mercado):
RUM = Universalidad * Intensidad * Claridad * Shareability * Distribución * Alineación

Todas las variables deben estar acotadas estrictamente en el rango [0.0, 1.0].
"""

from typing import Dict, Any, Tuple


def calculate_rum_score(metrics: Dict[str, float]) -> float:
    """
    Calcula el RUM Score a partir de las 6 variables fundamentales.
    
    :param metrics: Diccionario con las claves 'universalidad', 'intensidad',
                    'claridad', 'shareability', 'distribucion', 'alineacion'.
    :return: Float redondeado a 5 decimales.
    """
    required_keys = [
        "universalidad",
        "intensidad",
        "claridad",
        "shareability",
        "distribucion",
        "alineacion",
    ]

    for key in required_keys:
        if key not in metrics:
            raise KeyError(f"Falta la variable RUM obligatoria: '{key}'")
        
        val = float(metrics[key])
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"La variable RUM '{key}' debe estar acotada entre 0.0 y 1.0 (valor recibido: {val})"
            )

    score = (
        metrics["universalidad"]
        * metrics["intensidad"]
        * metrics["claridad"]
        * metrics["shareability"]
        * metrics["distribucion"]
        * metrics["alineacion"]
    )
    return round(score, 5)


def evaluate_rum_threshold(rum_score: float, threshold: float) -> Tuple[bool, float]:
    """
    Evalúa si un RUM score supera el umbral dinámico del nicho.
    
    :param rum_score: Score RUM calculado.
    :param threshold: Umbral dinámico del nicho.
    :return: Tupla (passes: bool, margin: float).
    """
    passes = rum_score >= threshold
    margin = round(rum_score - threshold, 5)
    return passes, margin
