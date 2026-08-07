"""
llm_budget_service.py

Servicio Enterprise para el seguimiento de consumo de tokens LLM, cálculo de costos en USD
y control de presupuestos mensuales por tenant con reserva atómica basada en Redis.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

MODEL_COST_PER_1M_PROMPT = {
    "gemini-1.5-flash": 0.075,
    "groq-llama-3-70b": 0.590,
    "gpt-4o-mini": 0.150,
}

MODEL_COST_PER_1M_COMPLETION = {
    "gemini-1.5-flash": 0.300,
    "groq-llama-3-70b": 0.790,
    "gpt-4o-mini": 0.600,
}

DEFAULT_TENANT_MONTHLY_BUDGET_USD = 20.00


def calculate_llm_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calcula el costo en USD basado en el modelo y conteo de tokens."""
    prompt_rate = MODEL_COST_PER_1M_PROMPT.get(model_name.lower(), 0.10) / 1_000_000
    completion_rate = MODEL_COST_PER_1M_COMPLETION.get(model_name.lower(), 0.40) / 1_000_000

    cost = (prompt_tokens * prompt_rate) + (completion_tokens * completion_rate)
    return round(cost, 6)


def track_llm_token_usage(
    tenant_id: str, model_name: str, prompt_tokens: int, completion_tokens: int
) -> Dict[str, Any]:
    """Registra una llamada LLM con su costo asociado e incrementa atómicamente el contador en Redis si está disponible."""
    cost_usd = calculate_llm_cost(model_name, prompt_tokens, completion_tokens)
    
    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        redis_key = f"llm_spend:{tenant_id}"
        new_total = r.incrbyfloat(redis_key, cost_usd)
        logger.info(f"[{tenant_id}] Consumo acumulado atómico en Redis: ${new_total:.6f} USD")
    except Exception as redis_err:
        # Pass-open por diseño: Redis es de resiliencia, no crítico para el flujo.
        # PERO debe ser visible para que los operadores sepan que el guard de presupuesto está inactivo.
        logger.warning(
            f"[{tenant_id}] ADVERTENCIA: No se pudo registrar consumo LLM en Redis ({redis_err}). "
            "El guard de presupuesto está INACTIVO para esta llamada. Verificar conectividad de Redis."
        )

    logger.info(f"[{tenant_id}] Consumo LLM: {model_name} | Tokens: {prompt_tokens}+{completion_tokens} | Costo: ${cost_usd:.6f} USD")

    return {
        "tenant_id": tenant_id,
        "model_name": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
    }


def check_tenant_llm_budget(
    tenant_id: str, accumulated_cost_usd: float, monthly_limit_usd: float = DEFAULT_TENANT_MONTHLY_BUDGET_USD
) -> bool:
    """Verifica si el tenant se encuentra dentro del presupuesto mensual permitido."""
    is_within_budget = accumulated_cost_usd <= monthly_limit_usd
    if not is_within_budget:
        logger.warning(f"[{tenant_id}] PRESUPUESTO LLM EXCEDIDO: ${accumulated_cost_usd:.2f} / ${monthly_limit_usd:.2f} USD")
    return is_within_budget
