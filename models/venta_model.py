"""Acceso a datos de ventas y sus detalles."""
from __future__ import annotations

from typing import Optional

from models.base_model import BaseModel, filtro_fechas


class VentaModel(BaseModel):
    def crear(self, fecha: str, total: int, observaciones: Optional[str] = None) -> int:
        cursor = self._ejecutar(
            "INSERT INTO ventas (fecha, total, estado, observaciones) VALUES (?, ?, 'CONFIRMADA', ?)",
            (fecha, total, observaciones),
        )
        return cursor.lastrowid

    def agregar_detalle(
        self, venta_id: int, producto_id: int, cantidad: int, precio_unitario: int, subtotal: int
    ) -> int:
        cursor = self._ejecutar(
            """INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario, subtotal)
               VALUES (?, ?, ?, ?, ?)""",
            (venta_id, producto_id, cantidad, precio_unitario, subtotal),
        )
        return cursor.lastrowid

    def marcar_anulada(self, venta_id: int) -> bool:
        """Pasa CONFIRMADA -> ANULADA. Devuelve False si no estaba confirmada."""
        cursor = self._ejecutar(
            "UPDATE ventas SET estado = 'ANULADA' WHERE id = ? AND estado = 'CONFIRMADA'",
            (venta_id,),
        )
        return cursor.rowcount == 1

    def obtener(self, venta_id: int) -> Optional[dict]:
        return self._uno(
            "SELECT id, fecha, total, estado, observaciones FROM ventas WHERE id = ?", (venta_id,)
        )

    def obtener_detalles(self, venta_id: int) -> list[dict]:
        return self._todos(
            """SELECT d.id, d.venta_id, d.producto_id, p.codigo, p.nombre AS producto,
                      p.unidad_medida, d.cantidad, d.precio_unitario, d.subtotal
               FROM detalle_venta d
               JOIN productos p ON p.id = d.producto_id
               WHERE d.venta_id = ?
               ORDER BY d.id""",
            (venta_id,),
        )

    def listar(
        self,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> list[dict]:
        condiciones, parametros = filtro_fechas("fecha", desde, hasta)
        if estado:
            condiciones.append("estado = ?")
            parametros.append(estado)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self._todos(
            "SELECT id, fecha, total, estado, observaciones FROM ventas"
            + where
            + " ORDER BY fecha DESC, id DESC",
            parametros,
        )

    def total_confirmado_del_dia(self, dia: str) -> int:
        """Suma de ventas CONFIRMADAS de un día 'AAAA-MM-DD' (las anuladas no cuentan)."""
        fila = self._uno(
            """SELECT COALESCE(SUM(total), 0) AS total FROM ventas
               WHERE estado = 'CONFIRMADA' AND fecha >= ? AND fecha < date(?, '+1 day')""",
            (dia, dia),
        )
        return int(fila["total"])

    def totales_por_dia(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> list[dict]:
        """Resumen diario separando ventas confirmadas de anuladas."""
        condiciones, parametros = filtro_fechas("fecha", desde, hasta)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self._todos(
            """SELECT substr(fecha, 1, 10) AS dia,
                      SUM(CASE WHEN estado = 'CONFIRMADA' THEN 1 ELSE 0 END) AS ventas_confirmadas,
                      COALESCE(SUM(CASE WHEN estado = 'CONFIRMADA' THEN total END), 0) AS total_confirmado,
                      SUM(CASE WHEN estado = 'ANULADA' THEN 1 ELSE 0 END) AS ventas_anuladas,
                      COALESCE(SUM(CASE WHEN estado = 'ANULADA' THEN total END), 0) AS total_anulado
               FROM ventas"""
            + where
            + " GROUP BY dia ORDER BY dia DESC",
            parametros,
        )
