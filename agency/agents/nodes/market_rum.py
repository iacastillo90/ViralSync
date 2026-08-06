"""
agents/nodes/market_rum.py

Helper para cálculo dinámico del umbral RUM por nicho y tenant.
(AGENTS.md sección 7.1)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agency:agency@localhost:5432/agency")
DEFAULT_THRESHOLD = 0.050  # percentil 70 por defecto para nichos sin suficiente histórico


def get_dynamic_threshold(tenant_id: str, niche: str) -> float:
    """
    Recupera el umbral RUM más reciente para (tenant_id, niche).
    Si no existe en DB, retorna el umbral por defecto (0.050).
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT threshold FROM rum_thresholds
                WHERE tenant_id = %s AND niche = %s
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                (tenant_id, niche),
            )
            row = cur.fetchone()
            conn.close()
            if row and row.get("threshold"):
                return float(row["threshold"])
    except Exception:
        pass  # Fallback a DEFAULT_THRESHOLD en dev/modo offline sin DB conectada

    return DEFAULT_THRESHOLD
