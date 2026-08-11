"""
circuit_breaker.py

Módulo de Circuit Breaker Asíncrono para resiliencia ante fallos en servicios externos
(Meta Instagram Graph API, SearXNG, LiteLLM Proxy).

Estados del circuito:
- CLOSED: Funcionamiento normal. Contabiliza fallos.
- OPEN: Circuito abierto por exceso de fallos. Retorna inmediatamente el fallback.
- HALF_OPEN: Transcurrido el cooldown, permite un intento de prueba. Si tiene éxito vuelve a CLOSED; si falla vuelve a OPEN.
"""

import time
import asyncio
import logging
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Excepción lanzada cuando el circuito está ABIERTO y no permite llamadas al servicio externo."""
    pass


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 10.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()

    def _update_state(self):
        now = time.time()
        if self.state == "OPEN" and (now - self.last_state_change) >= self.recovery_timeout:
            logger.info(f"[CircuitBreaker:{self.name}] Transicionando de OPEN a HALF_OPEN para prueba de salud.")
            self.state = "HALF_OPEN"
            self.last_state_change = now

    async def call(self, async_func: Callable[..., Any], fallback: Optional[Callable[..., Any]] = None, *args, **kwargs) -> Any:
        self._update_state()

        if self.state == "OPEN":
            logger.warning(f"[CircuitBreaker:{self.name}] Circuito ABIERTO. Usando fallback.")
            if fallback:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuito '{self.name}' abierto por fallos consecutivos.")

        try:
            if asyncio.iscoroutinefunction(async_func):
                result = await async_func(*args, **kwargs)
            else:
                result = async_func(*args, **kwargs)

            # Éxito: resetear contadores
            if self.state == "HALF_OPEN":
                logger.info(f"[CircuitBreaker:{self.name}] Prueba en HALF_OPEN exitosa. Reseteando a CLOSED.")
            self.state = "CLOSED"
            self.failure_count = 0
            return result

        except Exception as exc:
            self.failure_count += 1
            logger.warning(f"[CircuitBreaker:{self.name}] Fallo #{self.failure_count} registrado ({exc}).")

            if self.failure_count >= self.failure_threshold or self.state == "HALF_OPEN":
                self.state = "OPEN"
                self.last_state_change = time.time()
                logger.error(f"[CircuitBreaker:{self.name}] Umbral superado ({self.failure_count}). Circuito ABIERTO por {self.recovery_timeout}s.")

            if fallback:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
            raise


# Registro global de circuitos por nombre
_CIRCUITS: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, failure_threshold: int = 3, recovery_timeout: float = 10.0) -> CircuitBreaker:
    if name not in _CIRCUITS:
        _CIRCUITS[name] = CircuitBreaker(name, failure_threshold, recovery_timeout)
    return _CIRCUITS[name]
