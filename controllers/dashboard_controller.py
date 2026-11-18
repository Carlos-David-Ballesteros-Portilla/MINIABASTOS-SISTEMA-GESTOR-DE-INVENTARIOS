"""Controlador del panel principal."""
from __future__ import annotations

import sqlite3

from models.movimiento_model import MovimientoModel
from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from utils.formatters import hoy_iso

CANTIDAD_ULTIMOS_MOVIMIENTOS = 10


class DashboardController:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.productos = ProductoModel(conn)
        self.ventas = VentaModel(conn)
        self.movimientos = MovimientoModel(conn)

    def resumen(self) -> dict:
        return {
            "productos_activos": self.productos.contar_activos(),
            "stock_bajo": self.productos.contar_stock_bajo(),
            "agotados": self.productos.contar_agotados(),
            "ventas_hoy": self.ventas.total_confirmado_del_dia(hoy_iso()),
            "ultimos_movimientos": self.movimientos.ultimos(CANTIDAD_ULTIMOS_MOVIMIENTOS),
        }
