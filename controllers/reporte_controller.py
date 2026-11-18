"""Controlador de reportes (consultas de solo lectura)."""
from __future__ import annotations

import sqlite3
from typing import Optional

from models.movimiento_model import MovimientoModel
from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from services.inventario_service import clasificar_stock
from services.venta_service import VentaService
from utils.errors import ErrorNoEncontrado, ErrorValidacion
from utils.validators import parsear_fecha_opcional, validar_id, validar_rango_fechas

ESTADOS_VENTA = ("CONFIRMADA", "ANULADA")


class ReporteController:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.productos_modelo = ProductoModel(conn)
        self.movimientos_modelo = MovimientoModel(conn)
        self.ventas_modelo = VentaModel(conn)
        self.venta_servicio = VentaService(conn)

    @staticmethod
    def _rango(desde, hasta) -> tuple[Optional[str], Optional[str]]:
        desde = parsear_fecha_opcional(desde, "La fecha inicial")
        hasta = parsear_fecha_opcional(hasta, "La fecha final")
        validar_rango_fechas(desde, hasta)
        return desde, hasta

    def productos(self) -> list[dict]:
        """Todos los productos (activos e inactivos), para usar como filtro."""
        return self.productos_modelo.listar()

    def inventario_actual(self) -> list[dict]:
        filas = self.productos_modelo.listar()
        for fila in filas:
            fila["estado_stock"] = clasificar_stock(fila["stock_actual"], fila["stock_minimo"])
        return filas

    def movimientos(self, producto_id: Optional[int] = None, desde=None, hasta=None) -> list[dict]:
        desde, hasta = self._rango(desde, hasta)
        return self.movimientos_modelo.listar(producto_id, desde, hasta)

    def historial_ventas(self, desde=None, hasta=None, estado: Optional[str] = None) -> list[dict]:
        desde, hasta = self._rango(desde, hasta)
        if estado is not None and estado not in ESTADOS_VENTA:
            raise ErrorValidacion("Estado de venta inválido.")
        return self.ventas_modelo.listar(desde, hasta, estado)

    def detalle_venta(self, venta_id) -> dict:
        venta = self.venta_servicio.obtener_venta(validar_id(venta_id, "una venta"))
        if venta is None:
            raise ErrorNoEncontrado("La venta no existe.")
        return venta

    def totales_por_dia(self, desde=None, hasta=None) -> dict:
        """Total por día; el total vendido considera solo ventas CONFIRMADAS."""
        desde, hasta = self._rango(desde, hasta)
        filas = self.ventas_modelo.totales_por_dia(desde, hasta)
        return {"filas": filas, "total_confirmado": sum(f["total_confirmado"] for f in filas)}
