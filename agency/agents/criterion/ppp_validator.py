"""
ppp_validator.py

Validador de la Promesa Principal de Producto (PPP):
Estructura base: "Consigue [resultado] en [tiempo] sin [objeción principal]"
"""

import re
from typing import Dict, Any


def validate_ppp_structure(ppp_text: str) -> Dict[str, Any]:
    """
    Evalúa si un texto de PPP cumple con las reglas de concisión y estructura.
    
    :param ppp_text: Texto de la Promesa Principal de Producto.
    :return: Diccionario con el resultado de validación y detalles.
    """
    if not ppp_text or not isinstance(ppp_text, str):
        return {
            "valid": False,
            "reason": "La PPP no puede estar vacía ni ser nula.",
            "components_detected": {},
        }

    clean_text = ppp_text.strip()

    # Regla 1: Concisión (Máximo 35 palabras)
    words = clean_text.split()
    if len(words) > 35:
        return {
            "valid": False,
            "reason": f"La PPP es demasiado larga ({len(words)} palabras). Debe caber en una frase corta.",
            "components_detected": {},
        }

    # Regla 2: Presencia de ventana temporal ("en X días", "en X semanas", "en X meses", "en X horas", "en X minutos")
    time_pattern = re.compile(
        r"\ben\s+\d+\s+(días|dia|dias|semanas|semana|meses|mes|horas|hora|minutos|minuto)\b",
        re.IGNORECASE,
    )
    has_timeframe = bool(time_pattern.search(clean_text))

    # Regla 3: Presencia de remoción de objeción ("sin ...")
    objection_pattern = re.compile(r"\bsin\b", re.IGNORECASE)
    has_objection_removal = bool(objection_pattern.search(clean_text))

    is_valid = has_timeframe and has_objection_removal

    reason = "PPP válida y bien estructurada."
    if not is_valid:
        missing = []
        if not has_timeframe:
            missing.append("ventana de tiempo concreta ('en X días/semanas')")
        if not has_objection_removal:
            missing.append("remoción de objeción ('sin X')")
        reason = f"Falta incorporar: {', '.join(missing)}."

    return {
        "valid": is_valid,
        "reason": reason,
        "components_detected": {
            "has_timeframe": has_timeframe,
            "has_objection_removal": has_objection_removal,
            "word_count": len(words),
        },
    }
