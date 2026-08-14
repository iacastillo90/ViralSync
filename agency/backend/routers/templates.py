"""
templates.py

Router de Plantillas de Nicho e Industria (Fase 3A).
Provee plantillas pre-configuradas para agilizar el onboarding de nuevos productos/clientes en 1-click.
"""

import os
import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Plantillas de Nicho"])

TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "niche_templates.json")


@router.get("/niche-templates")
async def get_niche_templates() -> List[Dict[str, Any]]:
    """
    Retorna la lista de plantillas de nicho/industria disponibles para autocompletar el mapa de producto.
    """
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.error(f"Error leyendo plantillas de nicho: {exc}")

    # Fallback básico si falla el archivo
    return [
        {
            "id": "general",
            "name": "General / Producto o Servicio",
            "description": "Producto o servicio de campaña comercial.",
            "objections": "Precio, tiempo de entrega.",
            "target_desires": "Resultados rápidos e inversión segura.",
            "limiting_beliefs": "No saber por dónde comenzar.",
            "suggested_keyword": "SOLICITUD",
        }
    ]
