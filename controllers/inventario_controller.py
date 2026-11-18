"""Controlador de inventario: existencias, alertas, entradas, ajustes e historial."""
from __future__ import annotations

import sqlite3
from typing import Optional

from models.movimiento_model import MovimientoModel
from models.producto_model import ProductoModel
from services.inventario_service import InventarioService, clasificar_stock
from utils.errors import ErrorValidacion
from utils.validators import (
    parsear_cantidad,
    parsear_fecha_opcional,
    texto_opcional,
    validar_id,
    validar_rango_fechas,
)

DIRECCION_POSITIVO = "POSITIVO"
DIRECCION_NEGATIVO = "NEGATIVO"


class InventarioController:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.productos_modelo = ProductoModel(conn)
        self.movimientos_modelo = MovimientoModel(conn)
        self.servicio = InventarioService(conn)

    def productos(self, texto: Optional[str] = None, solo_activos: bool = False) -> list[dict]:
        return self._con_estado(self.productos_modelo.listar(texto=texto, solo_activos=solo_activos))

    def existencias(self, texto: Optional[str] = None, solo_alertas: bool = False) -> list[dict]:
        if solo_alertas:
            filas = self.servicio.alertas()
            if texto and texto.strip():
                criterio = texto.strip().lower()
                filas = [f for f in filas if criterio in f["codigo"].lower() or criterio in f["nombre"].lower()]
            return filas
        return self.productos(texto, solo_activos=True)

    def alertas(self) -> list[dict]:
        return self.servicio.alertas()

    def registrar_entrada(self, producto_id, cantidad, observacion=None) -> dict:
        return self.servicio.registrar_entrada(
            validar_id(producto_id, "un producto"),
            parsear_cantidad(cantidad, "La cantidad"),
            texto_opcional(observacion, "La observación"),
        )

    def registrar_ajuste(self, producto_id, direccion: str, cantidad, observacion) -> dict:
        producto_id = validar_id(producto_id, "un producto")
        cantidad_escalada = parsear_cantidad(cantidad, "La cantidad")
        if direccion == DIRECCION_POSITIVO:
            return self.servicio.registrar_ajuste_positivo(producto_id, cantidad_escalada, observacion)
        if direccion == DIRECCION_NEGATIVO:
            return self.servicio.registrar_ajuste_negativo(producto_id, cantidad_escalada, observacion)
        raise ErrorValidacion("Tipo de ajuste inválido.")

    def movimientos(
        self,
        producto_id: Optional[int] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        limite: Optional[int] = 500,
    ) -> list[dict]:
        desde = parsear_fecha_opcional(desde, "La fecha inicial")
        hasta = parsear_fecha_opcional(hasta, "La fecha final")
        validar_rango_fechas(desde, hasta)
        return self.movimientos_modelo.listar(producto_id, desde, hasta, limite)

    @staticmethod
    def _con_estado(filas: list[dict]) -> list[dict]:
        for fila in filas:
            fila["estado_stock"] = clasificar_stock(fila["stock_actual"], fila["stock_minimo"])
        return filas
