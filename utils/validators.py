"""Validación y conversión de datos de entrada (texto -> tipos de dominio).

Convenciones de entrada:
  * Cantidades: hasta 3 decimales; se acepta coma o punto como separador
    decimal ("0,5", "1.250" = 1,25). No se aceptan separadores de miles.
  * Precios: enteros en COP; se acepta "2500", "$2.500" (el punto solo como
    separador de miles).
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from utils.calculos import (
    ESCALA_CANTIDAD,
    MAX_CANTIDAD_ESCALADA,
    MAX_CANTIDAD_UNIDADES,
    MAX_PRECIO,
)
from utils.errors import ErrorValidacion

_RE_CANTIDAD = re.compile(r"\d+(?:[.,]\d{1,3})?")
_RE_CANTIDAD_MUCHOS_DECIMALES = re.compile(r"\d+[.,]\d{4,}")
_RE_PRECIO_SIMPLE = re.compile(r"\d+")
_RE_PRECIO_MILES = re.compile(r"\d{1,3}(?:\.\d{3})+")


def _como_texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def texto_obligatorio(valor, campo: str, max_len: int = 200) -> str:
    texto = _como_texto(valor)
    if not texto:
        raise ErrorValidacion(f"{campo} es obligatorio.")
    if len(texto) > max_len:
        raise ErrorValidacion(f"{campo} no puede superar {max_len} caracteres.")
    return texto


def texto_opcional(valor, campo: str = "El texto", max_len: int = 500) -> Optional[str]:
    texto = _como_texto(valor)
    if not texto:
        return None
    if len(texto) > max_len:
        raise ErrorValidacion(f"{campo} no puede superar {max_len} caracteres.")
    return texto


def validar_id(valor, campo: str = "el registro") -> int:
    if valor is None or isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErrorValidacion(f"Seleccione {campo}.")
    return valor


def parsear_cantidad(
    texto,
    campo: str = "La cantidad",
    permitir_cero: bool = False,
    vacio_es_cero: bool = False,
) -> int:
    """Convierte texto a cantidad escalada x1000 usando Decimal."""
    limpio = _como_texto(texto)
    if not limpio:
        if vacio_es_cero:
            return 0
        raise ErrorValidacion(f"{campo} es obligatoria.")
    if limpio.startswith("-"):
        raise ErrorValidacion(f"{campo} no puede ser un valor negativo.")
    if _RE_CANTIDAD_MUCHOS_DECIMALES.fullmatch(limpio):
        raise ErrorValidacion(f"{campo} admite como máximo 3 decimales.")
    if not _RE_CANTIDAD.fullmatch(limpio):
        raise ErrorValidacion(
            f"{campo} no es un número válido (ejemplos: 2, 0,5, 1,250)."
        )
    escalada = int(Decimal(limpio.replace(",", ".")) * ESCALA_CANTIDAD)
    if escalada == 0 and not permitir_cero:
        raise ErrorValidacion(f"{campo} debe ser mayor que cero.")
    if escalada > MAX_CANTIDAD_ESCALADA:
        raise ErrorValidacion(
            f"{campo} no puede superar {MAX_CANTIDAD_UNIDADES:,} unidades.".replace(",", ".")
        )
    return escalada


def parsear_precio(texto, campo: str = "El precio", vacio_es_cero: bool = False) -> int:
    """Convierte texto a pesos enteros (COP). El resultado es >= 0."""
    limpio = _como_texto(texto).replace("$", "").replace(" ", "")
    if not limpio:
        if vacio_es_cero:
            return 0
        raise ErrorValidacion(f"{campo} es obligatorio.")
    if limpio.startswith("-"):
        raise ErrorValidacion(f"{campo} no puede ser un valor negativo.")
    if _RE_PRECIO_SIMPLE.fullmatch(limpio):
        valor = int(limpio)
    elif _RE_PRECIO_MILES.fullmatch(limpio):
        valor = int(limpio.replace(".", ""))
    else:
        raise ErrorValidacion(
            f"{campo} debe ser un número entero en pesos (ejemplos: 2500, $2.500)."
        )
    if valor > MAX_PRECIO:
        raise ErrorValidacion(f"{campo} es demasiado alto.")
    return valor


def parsear_fecha_opcional(texto, campo: str = "La fecha") -> Optional[str]:
    """Devuelve 'AAAA-MM-DD' o None si el texto está vacío."""
    limpio = _como_texto(texto)
    if not limpio:
        return None
    try:
        return datetime.strptime(limpio, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ErrorValidacion(
            f"{campo} debe tener el formato AAAA-MM-DD (por ejemplo, 2026-11-17)."
        ) from None


def validar_rango_fechas(desde: Optional[str], hasta: Optional[str]) -> None:
    if desde and hasta and desde > hasta:
        raise ErrorValidacion("La fecha inicial no puede ser posterior a la final.")
