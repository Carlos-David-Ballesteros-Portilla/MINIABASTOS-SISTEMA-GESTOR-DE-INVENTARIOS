"""Servicio de ventas: confirmación y anulación, siempre en una única transacción."""
from __future__ import annotations

import sqlite3
from typing import Optional

from database.connection import transaccion
from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from services.inventario_service import InventarioService
from utils.calculos import calcular_subtotal, calcular_total
from utils.errors import (
    ErrorEstadoInvalido,
    ErrorNoEncontrado,
    ErrorStockInsuficiente,
    ErrorValidacion,
)
from utils.formatters import ahora_iso, formatear_cantidad


def _es_entero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


class VentaService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.productos = ProductoModel(conn)
        self.ventas = VentaModel(conn)
        self.inventario = InventarioService(conn)

    # --- Confirmación ----------------------------------------------------------------

    def confirmar_venta(
        self, items: list[dict], observaciones: Optional[str] = None, fecha: Optional[str] = None
    ) -> dict:
        """Registra una venta completa o no registra nada.

        ``items``: lista de ``{"producto_id", "cantidad" (x1000), "precio_unitario" (COP)}``.
        """
        lineas = self._consolidar(items)
        fecha = fecha or ahora_iso()
        with transaccion(self.conn):
            productos = self._validar_productos_activos(lineas)
            self._validar_stock(lineas, productos)
            for linea in lineas:
                linea["subtotal"] = calcular_subtotal(linea["cantidad"], linea["precio_unitario"])
            total = calcular_total(linea["subtotal"] for linea in lineas)

            venta_id = self.ventas.crear(fecha, total, observaciones)
            for linea in lineas:
                detalle_id = self.ventas.agregar_detalle(
                    venta_id, linea["producto_id"], linea["cantidad"],
                    linea["precio_unitario"], linea["subtotal"],
                )
                self.inventario.registrar_salida_venta(
                    linea["producto_id"], linea["cantidad"], detalle_id, f"Venta #{venta_id}", fecha
                )
        return self.obtener_venta(venta_id)

    # --- Anulación -----------------------------------------------------------------------

    def anular_venta(self, venta_id: int, fecha: Optional[str] = None) -> dict:
        fecha = fecha or ahora_iso()
        with transaccion(self.conn):
            venta = self.ventas.obtener(venta_id)
            if venta is None:
                raise ErrorNoEncontrado("La venta no existe.")
            if venta["estado"] != "CONFIRMADA":
                raise ErrorEstadoInvalido(f"La venta #{venta_id} ya está anulada.")
            for detalle in self.ventas.obtener_detalles(venta_id):
                self.inventario.registrar_reversion_venta(
                    detalle["producto_id"], detalle["cantidad"], detalle["id"],
                    f"Anulación de la venta #{venta_id}", fecha,
                )
            if not self.ventas.marcar_anulada(venta_id):
                raise ErrorEstadoInvalido(f"La venta #{venta_id} ya está anulada.")
        return self.obtener_venta(venta_id)

    # --- Consulta ----------------------------------------------------------------------------

    def obtener_venta(self, venta_id: int) -> Optional[dict]:
        venta = self.ventas.obtener(venta_id)
        if venta is not None:
            venta["detalles"] = self.ventas.obtener_detalles(venta_id)
        return venta

    # --- Validaciones internas ------------------------------------------------------------------

    @staticmethod
    def _consolidar(items: list[dict]) -> list[dict]:
        """Valida cada ítem y acumula cantidades de un mismo producto en una sola línea."""
        if not items:
            raise ErrorValidacion("La venta debe contener al menos un producto.")
        lineas: dict[int, dict] = {}
        for item in items:
            producto_id = item.get("producto_id")
            cantidad = item.get("cantidad")
            precio = item.get("precio_unitario")
            if not _es_entero(producto_id):
                raise ErrorValidacion("Producto inválido en la venta.")
            if not _es_entero(cantidad) or cantidad <= 0:
                raise ErrorValidacion("Todas las cantidades deben ser mayores que cero.")
            if not _es_entero(precio) or precio < 0:
                raise ErrorValidacion("Los precios no pueden ser negativos.")
            existente = lineas.get(producto_id)
            if existente is None:
                lineas[producto_id] = {"producto_id": producto_id, "cantidad": cantidad, "precio_unitario": precio}
            elif existente["precio_unitario"] != precio:
                raise ErrorValidacion("Un mismo producto no puede tener dos precios distintos en la venta.")
            else:
                existente["cantidad"] += cantidad
        return list(lineas.values())

    def _validar_productos_activos(self, lineas: list[dict]) -> dict[int, dict]:
        productos: dict[int, dict] = {}
        for linea in lineas:
            producto = self.productos.obtener(linea["producto_id"])
            if producto is None:
                raise ErrorNoEncontrado("Uno de los productos de la venta no existe.")
            if not producto["activo"]:
                raise ErrorValidacion(
                    f"El producto {producto['nombre']} está desactivado y no puede venderse."
                )
            productos[linea["producto_id"]] = producto
        return productos

    @staticmethod
    def _validar_stock(lineas: list[dict], productos: dict[int, dict]) -> None:
        faltantes = []
        for linea in lineas:
            producto = productos[linea["producto_id"]]
            if producto["stock_actual"] < linea["cantidad"]:
                faltantes.append(
                    f"{producto['nombre']} (disponible {formatear_cantidad(producto['stock_actual'])} "
                    f"{producto['unidad_medida']}, solicitado {formatear_cantidad(linea['cantidad'])} {producto['unidad_medida']})"
                )
        if faltantes:
            raise ErrorStockInsuficiente("Existencias insuficientes para: " + "; ".join(faltantes) + ".")
