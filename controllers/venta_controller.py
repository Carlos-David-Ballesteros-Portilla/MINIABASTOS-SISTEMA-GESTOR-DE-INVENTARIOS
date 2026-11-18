"""Controlador de ventas: mantiene el borrador (carrito) y delega en VentaService.

Regla de acumulación: si un producto se agrega de nuevo, su cantidad se suma
en la misma línea y se aplica el precio indicado en esa última adición
(si no se indica, el precio vigente del producto).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from services.venta_service import VentaService
from utils.calculos import MAX_CANTIDAD_ESCALADA, calcular_subtotal, calcular_total
from utils.errors import ErrorNoEncontrado, ErrorValidacion
from utils.validators import (
    parsear_cantidad,
    parsear_fecha_opcional,
    parsear_precio,
    texto_opcional,
    validar_id,
    validar_rango_fechas,
)

ESTADOS_VENTA = ("CONFIRMADA", "ANULADA")


class VentaController:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.productos = ProductoModel(conn)
        self.ventas_modelo = VentaModel(conn)
        self.servicio = VentaService(conn)
        self._carrito: dict[int, dict] = {}

    # --- Búsqueda de productos vendibles -----------------------------------------------

    def buscar_productos(self, texto: Optional[str] = None) -> list[dict]:
        """Solo productos activos: los desactivados no aparecen en nuevas ventas."""
        return self.productos.listar(texto=texto, solo_activos=True)

    # --- Borrador de venta -------------------------------------------------------------------

    def obtener_carrito(self) -> dict:
        lineas = list(self._carrito.values())
        return {"lineas": [dict(linea) for linea in lineas], "total": calcular_total(l["subtotal"] for l in lineas)}

    def agregar_al_carrito(self, producto_id, cantidad, precio=None) -> dict:
        producto_id = validar_id(producto_id, "un producto")
        cantidad_escalada = parsear_cantidad(cantidad, "La cantidad")
        producto = self.productos.obtener(producto_id)
        if producto is None:
            raise ErrorNoEncontrado("El producto no existe.")
        if not producto["activo"]:
            raise ErrorValidacion("El producto está desactivado y no puede venderse.")
        if precio is not None and str(precio).strip():
            precio_unitario = parsear_precio(precio, "El precio")
        else:
            precio_unitario = producto["precio_venta"]

        linea = self._carrito.get(producto_id)
        if linea is None:
            linea = {
                "producto_id": producto_id,
                "codigo": producto["codigo"],
                "nombre": producto["nombre"],
                "unidad_medida": producto["unidad_medida"],
                "cantidad": 0,
            }
        nueva_cantidad = linea["cantidad"] + cantidad_escalada
        if nueva_cantidad > MAX_CANTIDAD_ESCALADA:
            raise ErrorValidacion("La cantidad acumulada del producto es demasiado grande.")
        linea["cantidad"] = nueva_cantidad
        linea["precio_unitario"] = precio_unitario
        linea["subtotal"] = calcular_subtotal(linea["cantidad"], precio_unitario)
        self._carrito[producto_id] = linea
        return self.obtener_carrito()

    def quitar_del_carrito(self, producto_id) -> dict:
        self._carrito.pop(validar_id(producto_id, "una línea de la venta"), None)
        return self.obtener_carrito()

    def vaciar_carrito(self) -> None:
        self._carrito.clear()

    def confirmar_venta(self, observaciones=None) -> dict:
        """Confirma la venta del carrito. Si falla, el carrito se conserva para corregirlo."""
        items = [
            {"producto_id": l["producto_id"], "cantidad": l["cantidad"], "precio_unitario": l["precio_unitario"]}
            for l in self._carrito.values()
        ]
        venta = self.servicio.confirmar_venta(items, texto_opcional(observaciones, "Las observaciones"))
        self._carrito.clear()
        return venta

    # --- Historial y anulación ---------------------------------------------------------------------

    def ventas(self, desde=None, hasta=None, estado: Optional[str] = None) -> list[dict]:
        desde = parsear_fecha_opcional(desde, "La fecha inicial")
        hasta = parsear_fecha_opcional(hasta, "La fecha final")
        validar_rango_fechas(desde, hasta)
        if estado is not None and estado not in ESTADOS_VENTA:
            raise ErrorValidacion("Estado de venta inválido.")
        return self.ventas_modelo.listar(desde, hasta, estado)

    def detalle_venta(self, venta_id) -> dict:
        venta = self.servicio.obtener_venta(validar_id(venta_id, "una venta"))
        if venta is None:
            raise ErrorNoEncontrado("La venta no existe.")
        return venta

    def anular_venta(self, venta_id) -> dict:
        return self.servicio.anular_venta(validar_id(venta_id, "una venta"))
