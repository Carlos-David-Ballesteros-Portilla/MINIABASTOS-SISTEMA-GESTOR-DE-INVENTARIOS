"""Servicio de inventario: único punto que modifica ``stock_actual``.

Cada cambio de existencias se hace en la misma transacción que el movimiento
que lo justifica, por lo que ``stock_actual`` y los movimientos no pueden
quedar desincronizados.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from database.connection import transaccion
from models.movimiento_model import MovimientoModel
from models.producto_model import ProductoModel
from utils.errors import ErrorNoEncontrado, ErrorStockInsuficiente, ErrorValidacion
from utils.formatters import ahora_iso, formatear_cantidad

ENTRADA = "ENTRADA"
SALIDA = "SALIDA"
AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"

TIPOS_QUE_SUMAN = (ENTRADA, AJUSTE_POSITIVO)
TIPOS_QUE_RESTAN = (SALIDA, AJUSTE_NEGATIVO)

ESTADO_AGOTADO = "AGOTADO"
ESTADO_BAJO = "BAJO"
ESTADO_OK = "OK"


def clasificar_stock(stock_actual: int, stock_minimo: int) -> str:
    """AGOTADO (0), BAJO (0 < stock <= mínimo) u OK."""
    if stock_actual <= 0:
        return ESTADO_AGOTADO
    if stock_actual <= stock_minimo:
        return ESTADO_BAJO
    return ESTADO_OK


def _es_entero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


class InventarioService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.productos = ProductoModel(conn)
        self.movimientos = MovimientoModel(conn)

    # --- Operaciones manuales -------------------------------------------------

    def registrar_entrada(
        self, producto_id: int, cantidad: int, observacion: Optional[str] = None, fecha: Optional[str] = None
    ) -> dict:
        return self._aplicar(producto_id, ENTRADA, cantidad, observacion, None, fecha)

    def registrar_ajuste_positivo(
        self, producto_id: int, cantidad: int, observacion: str, fecha: Optional[str] = None
    ) -> dict:
        return self._aplicar(producto_id, AJUSTE_POSITIVO, cantidad, self._observacion_ajuste(observacion), None, fecha)

    def registrar_ajuste_negativo(
        self, producto_id: int, cantidad: int, observacion: str, fecha: Optional[str] = None
    ) -> dict:
        return self._aplicar(producto_id, AJUSTE_NEGATIVO, cantidad, self._observacion_ajuste(observacion), None, fecha)

    # --- Operaciones originadas en ventas (las usa VentaService) -------------------

    def registrar_salida_venta(
        self, producto_id: int, cantidad: int, detalle_venta_id: int,
        observacion: Optional[str] = None, fecha: Optional[str] = None,
    ) -> dict:
        return self._aplicar(producto_id, SALIDA, cantidad, observacion, detalle_venta_id, fecha)

    def registrar_reversion_venta(
        self, producto_id: int, cantidad: int, detalle_venta_id: int,
        observacion: Optional[str] = None, fecha: Optional[str] = None,
    ) -> dict:
        """Reversión por anulación: ENTRADA que referencia el mismo detalle de venta."""
        return self._aplicar(producto_id, ENTRADA, cantidad, observacion, detalle_venta_id, fecha)

    # --- Consultas ---------------------------------------------------------------

    def alertas(self) -> list[dict]:
        """Productos activos con existencias <= stock mínimo, con su clasificación."""
        filas = self.productos.alertas()
        for fila in filas:
            fila["estado_stock"] = clasificar_stock(fila["stock_actual"], fila["stock_minimo"])
        return filas

    def verificar_coherencia(self) -> list[dict]:
        """Lista vacía = stock_actual coincide con la suma de movimientos en todos los productos."""
        return self.movimientos.discrepancias_de_stock()

    # --- Interno -----------------------------------------------------------------

    @staticmethod
    def _observacion_ajuste(observacion: Optional[str]) -> str:
        texto = (observacion or "").strip()
        if not texto:
            raise ErrorValidacion("Los ajustes de inventario requieren una observación.")
        return texto

    def _aplicar(
        self,
        producto_id: int,
        tipo: str,
        cantidad: int,
        observacion: Optional[str],
        detalle_venta_id: Optional[int],
        fecha: Optional[str],
    ) -> dict:
        if not _es_entero(cantidad) or cantidad <= 0:
            raise ErrorValidacion("La cantidad del movimiento debe ser un entero escalado mayor que cero.")
        fecha = fecha or ahora_iso()
        with transaccion(self.conn):
            producto = self.productos.obtener(producto_id)
            if producto is None:
                raise ErrorNoEncontrado("El producto no existe.")
            anterior = producto["stock_actual"]
            posterior = anterior + cantidad if tipo in TIPOS_QUE_SUMAN else anterior - cantidad
            if posterior < 0:
                raise ErrorStockInsuficiente(
                    f"Existencias insuficientes de {producto['nombre']}: disponible "
                    f"{formatear_cantidad(anterior)} {producto['unidad_medida']}, "
                    f"se intentó descontar {formatear_cantidad(cantidad)}."
                )
            self.productos.actualizar_stock(producto_id, posterior)
            movimiento_id = self.movimientos.registrar(
                producto_id, tipo, cantidad, anterior, posterior, fecha, observacion, detalle_venta_id
            )
            return self.movimientos.obtener(movimiento_id)
