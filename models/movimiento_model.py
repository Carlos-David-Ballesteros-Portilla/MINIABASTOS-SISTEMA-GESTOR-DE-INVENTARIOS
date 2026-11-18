"""Acceso a datos de movimientos de inventario (solo inserción y consulta)."""
from __future__ import annotations

from typing import Optional

from models.base_model import BaseModel, filtro_fechas

_SELECT = """
    SELECT m.id, m.fecha, m.producto_id, p.codigo, p.nombre AS producto,
           p.unidad_medida, m.tipo, m.cantidad, m.stock_anterior, m.stock_posterior,
           m.detalle_venta_id, d.venta_id, m.observacion
    FROM movimientos_inventario m
    JOIN productos p ON p.id = m.producto_id
    LEFT JOIN detalle_venta d ON d.id = m.detalle_venta_id
"""


class MovimientoModel(BaseModel):
    def registrar(
        self,
        producto_id: int,
        tipo: str,
        cantidad: int,
        stock_anterior: int,
        stock_posterior: int,
        fecha: str,
        observacion: Optional[str] = None,
        detalle_venta_id: Optional[int] = None,
    ) -> int:
        cursor = self._ejecutar(
            """INSERT INTO movimientos_inventario
                   (producto_id, tipo, cantidad, stock_anterior, stock_posterior,
                    detalle_venta_id, fecha, observacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (producto_id, tipo, cantidad, stock_anterior, stock_posterior, detalle_venta_id, fecha, observacion),
        )
        return cursor.lastrowid

    def obtener(self, movimiento_id: int) -> Optional[dict]:
        return self._uno(_SELECT + " WHERE m.id = ?", (movimiento_id,))

    def listar(
        self,
        producto_id: Optional[int] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> list[dict]:
        condiciones, parametros = filtro_fechas("m.fecha", desde, hasta)
        if producto_id is not None:
            condiciones.append("m.producto_id = ?")
            parametros.append(producto_id)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        sql = _SELECT + where + " ORDER BY m.fecha DESC, m.id DESC"
        if limite:
            sql += " LIMIT ?"
            parametros.append(int(limite))
        return self._todos(sql, parametros)

    def ultimos(self, cantidad: int = 10) -> list[dict]:
        return self.listar(limite=cantidad)

    def discrepancias_de_stock(self) -> list[dict]:
        """Productos cuyo stock_actual no coincide con la suma de sus movimientos."""
        return self._todos(
            """SELECT p.id AS producto_id, p.codigo, p.stock_actual,
                      COALESCE(SUM(CASE WHEN m.tipo IN ('ENTRADA', 'AJUSTE_POSITIVO')
                                        THEN m.cantidad ELSE -m.cantidad END), 0) AS stock_segun_movimientos
               FROM productos p
               LEFT JOIN movimientos_inventario m ON m.producto_id = p.id
               GROUP BY p.id
               HAVING p.stock_actual <> stock_segun_movimientos
               ORDER BY p.id"""
        )
