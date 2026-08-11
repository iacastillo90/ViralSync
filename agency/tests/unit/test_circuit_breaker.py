"""
test_circuit_breaker.py

Pruebas unitarias de contrato (TDD) para la Fase 3: Resiliencia y Circuit Breakers.
"""

import pytest
import asyncio
from backend.security.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=0.2)
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0


def test_circuit_breaker_opens_on_failures():
    async def _test():
        cb = CircuitBreaker("test_fail", failure_threshold=2, recovery_timeout=0.2)

        async def failing_func():
            raise ValueError("Error simulado de API externa")

        def fallback_func():
            return "fallback_result"

        # Primer fallo
        res1 = await cb.call(failing_func, fallback=fallback_func)
        assert res1 == "fallback_result"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1

        # Segundo fallo -> abre circuito
        res2 = await cb.call(failing_func, fallback=fallback_func)
        assert res2 == "fallback_result"
        assert cb.state == "OPEN"

        # Tercer intento cuando está OPEN debe usar fallback sin llamar a la función
        res3 = await cb.call(failing_func, fallback=fallback_func)
        assert res3 == "fallback_result"

    asyncio.run(_test())


def test_circuit_breaker_half_open_recovery():
    async def _test():
        cb = CircuitBreaker("test_recovery", failure_threshold=1, recovery_timeout=0.1)

        async def failing_func():
            raise ValueError("Fail")

        async def success_func():
            return "ok"

        # Forzar apertura
        await cb.call(failing_func, fallback=lambda: "fallback")
        assert cb.state == "OPEN"

        # Esperar timeout de recuperación
        await asyncio.sleep(0.15)

        # El siguiente call debe intentar en HALF_OPEN y volver a CLOSED al tener éxito
        res = await cb.call(success_func)
        assert res == "ok"
        assert cb.state == "CLOSED"

    asyncio.run(_test())
