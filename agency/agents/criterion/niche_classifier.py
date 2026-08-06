"""
niche_classifier.py

Clasificador Inteligente de Tipo de Negocio:
Distingue entre PRODUCTO_FISICO (requiere demostración visual e Image-to-Video)
y SERVICIO_INTANGIBLE (requiere demostración de valor, dolor del cliente y autoridad).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def classify_business_type(description: str, user_choice: str = "auto") -> Dict[str, Any]:
    """
    Clasifica si la descripción ingresada corresponde a un Producto Físico o Servicio Intangible.

    :param description: Texto descriptivo del producto/servicio.
    :param user_choice: Elección manual del usuario ('auto', 'PRODUCTO_FISICO', 'SERVICIO_INTANGIBLE').
    :return: Diccionario con la clasificación, confianza y recomendación de estrategia visual.
    """
    if user_choice in ["PRODUCTO_FISICO", "SERVICIO_INTANGIBLE"]:
        business_type = user_choice
    else:
        # Palabras clave orientadas a producto físico vs servicio
        product_keywords = [
            "producto", "zapato", "zapatilla", "zapatillas", "tenis", "calzado", "ropa",
            "suplemento", "suplementos", "crema", "cremas", "gadget", "físico", "física",
            "botella", "envío", "caja", "tienda", "e-commerce", "hardware", "accesorio", "suela"
        ]
        desc_lower = description.lower()
        is_product = any(kw in desc_lower for kw in product_keywords)
        business_type = "PRODUCTO_FISICO" if is_product else "SERVICIO_INTANGIBLE"

    logger.info(f"Clasificación de negocio determinada: {business_type}")

    if business_type == "PRODUCTO_FISICO":
        strategy = {
            "business_type": "PRODUCTO_FISICO",
            "visual_mode": "IMAGE_TO_VIDEO",
            "narrative_focus": "Demostración del producto real, textura, uso práctico y unboxing visual.",
        }
    else:
        strategy = {
            "business_type": "SERVICIO_INTANGIBLE",
            "visual_mode": "TEXT_TO_VIDEO",
            "narrative_focus": "Transformación de cliente, eliminación de fricción y llamado a la acción claro.",
        }

    return strategy
