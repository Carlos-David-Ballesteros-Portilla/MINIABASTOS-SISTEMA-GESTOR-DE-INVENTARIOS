"""Conversión de cantidades y cálculos monetarios.

Cantidades
----------
Todas las cantidades se almacenan como ``INTEGER`` escalado por 1000
(tres posiciones decimales): 1 unidad = 1000, 0,5 kg = 500, 1,250 kg = 1250.
Las conversiones usan ``Decimal``; nunca ``float``.

Dinero y criterio de redondeo
-----------------------------
Los precios son enteros en pesos colombianos (COP). El subtotal de cada línea es:

    subtotal = redondear(cantidad_decimal * precio_unitario)

El redondeo se hace UNA sola vez por línea, a pesos enteros, con
``Decimal`` y ``ROUND_HALF_UP`` (la mitad se redondea hacia arriba:
12,5 -> 13). El total de la venta es la suma de los subtotales ya redondeados
(no se redondea el total de nuevo).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

ESCALA_CANTIDAD = 1000

# Límites defensivos: evitan desbordar el INTEGER de 64 bits de SQLite.
MAX_CANTIDAD_UNIDADES = 1_000_000
MAX_CANTIDAD_ESCALADA = MAX_CANTIDAD_UNIDADES * ESCALA_CANTIDAD
MAX_PRECIO = 1_000_000_000


def escalada_a_decimal(cantidad_escalada: int) -> Decimal:
    """Convierte una cantidad almacenada (x1000) a su valor decimal real."""
    return Decimal(cantidad_escalada) / ESCALA_CANTIDAD


def calcular_subtotal(cantidad_escalada: int, precio_unitario: int) -> int:
    """Subtotal en COP, redondeado con ROUND_HALF_UP a pesos enteros."""
    bruto = escalada_a_decimal(cantidad_escalada) * Decimal(precio_unitario)
    return int(bruto.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def calcular_total(subtotales: Iterable[int]) -> int:
    """El total es la suma de subtotales ya redondeados."""
    return sum(subtotales)
