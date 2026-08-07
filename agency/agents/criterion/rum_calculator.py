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
    
    :param rum_score: Score RUM calculated.
    :param threshold: Umbral dinámico del nicho.
    :return: Tupla (passes: bool, margin: float).
    """
    passes = rum_score >= threshold
    margin = round(rum_score - threshold, 5)
    return passes, margin


def get_dynamic_threshold(niche: str) -> float:
    """
    Obtiene el umbral dinámico del nicho desde Redis (recalibrado cada 72h con EMA).
    Aplica una salvaguarda de clamp estricta entre [0.50, 0.90] para evitar bloqueos por outliers.
    """
    import os
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    default_threshold = 0.70

    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        val = r.get(f"rum_threshold:{niche}")
        if val:
            threshold = float(val)
            # Clamp guardia [0.50, 0.90]
            return max(0.50, min(0.90, round(threshold, 2)))
    except Exception:
        pass

    return default_threshold
