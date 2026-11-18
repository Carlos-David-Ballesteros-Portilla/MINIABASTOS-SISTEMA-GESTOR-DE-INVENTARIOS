"""Formato de presentación de cantidades, dinero, fechas y etiquetas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from utils.calculos import ESCALA_CANTIDAD

ETIQUETAS_TIPO_MOVIMIENTO = {
    "ENTRADA": "Entrada",
    "SALIDA": "Salida",
    "AJUSTE_POSITIVO": "Ajuste (+)",
    "AJUSTE_NEGATIVO": "Ajuste (-)",
}

ETIQUETAS_ESTADO_STOCK = {
    "AGOTADO": "Agotado",
    "BAJO": "Stock bajo",
    "OK": "Normal",
}


def formatear_cantidad(cantidad_escalada: int) -> str:
    """1000 -> '1'; 500 -> '0,5'; 1250 -> '1,25'. Nunca muestra el valor escalado.

    Usa coma decimal y sin separador de miles, de modo que el texto mostrado
    pueda volver a editarse y convertirse sin ambigüedad.
    """
    valor = Decimal(cantidad_escalada) / ESCALA_CANTIDAD
    signo = "-" if valor < 0 else ""
    entero, _, decimales = f"{abs(valor):.3f}".partition(".")
    decimales = decimales.rstrip("0")
    return f"{signo}{entero}" + (f",{decimales}" if decimales else "")


def formatear_moneda(pesos: int) -> str:
    """2500 -> '$2.500'."""
    signo = "-" if pesos < 0 else ""
    return f"{signo}${abs(pesos):,}".replace(",", ".")


def formatear_tipo_movimiento(tipo: str) -> str:
    return ETIQUETAS_TIPO_MOVIMIENTO.get(tipo, tipo)


def formatear_estado_stock(estado: str) -> str:
    return ETIQUETAS_ESTADO_STOCK.get(estado, estado)


def ahora_iso() -> str:
    """Fecha y hora local con formato 'AAAA-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hoy_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")
