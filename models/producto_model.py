"""Acceso a datos de productos."""
from __future__ import annotations

from typing import Optional

from models.base_model import BaseModel

_SELECT = """
    SELECT p.id, p.codigo, p.nombre, p.descripcion, p.unidad_medida,
           p.categoria_id, c.nombre AS categoria,
           p.precio_venta, p.stock_actual, p.stock_minimo, p.activo
    FROM productos p
    JOIN categorias c ON c.id = p.categoria_id
"""

_ESCAPE = "\\"


def _patron_like(texto: str) -> str:
    """Escapa %, _ y \\ para que la búsqueda sea literal."""
    escapado = (
        texto.replace(_ESCAPE, _ESCAPE * 2).replace("%", _ESCAPE + "%").replace("_", _ESCAPE + "_")
    )
    return f"%{escapado}%"


class ProductoModel(BaseModel):
    def crear(
        self,
        codigo: str,
        nombre: str,
        descripcion: Optional[str],
        unidad_medida: str,
        categoria_id: int,
        precio_venta: int,
        stock_minimo: int,
    ) -> int:
        """Crea un producto con existencias en 0 (el stock solo cambia vía movimientos)."""
        cursor = self._ejecutar(
            """INSERT INTO productos
                   (codigo, nombre, descripcion, unidad_medida, categoria_id,
                    precio_venta, stock_actual, stock_minimo, activo)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, 1)""",
            (codigo, nombre, descripcion, unidad_medida, categoria_id, precio_venta, stock_minimo),
        )
        return cursor.lastrowid

    def actualizar(
        self,
        producto_id: int,
        codigo: str,
        nombre: str,
        descripcion: Optional[str],
        unidad_medida: str,
        categoria_id: int,
        precio_venta: int,
        stock_minimo: int,
    ) -> bool:
        """Modifica datos del producto. No toca stock_actual."""
        cursor = self._ejecutar(
            """UPDATE productos
               SET codigo = ?, nombre = ?, descripcion = ?, unidad_medida = ?,
                   categoria_id = ?, precio_venta = ?, stock_minimo = ?
               WHERE id = ?""",
            (codigo, nombre, descripcion, unidad_medida, categoria_id, precio_venta, stock_minimo, producto_id),
        )
        return cursor.rowcount > 0

    def cambiar_estado(self, producto_id: int, activo: bool) -> bool:
        cursor = self._ejecutar(
            "UPDATE productos SET activo = ? WHERE id = ?", (1 if activo else 0, producto_id)
        )
        return cursor.rowcount > 0

    def actualizar_stock(self, producto_id: int, nuevo_stock: int) -> bool:
        """Uso exclusivo de InventarioService: siempre acompañado de un movimiento."""
        cursor = self._ejecutar(
            "UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, producto_id)
        )
        return cursor.rowcount > 0

    def obtener(self, producto_id: int) -> Optional[dict]:
        return self._uno(_SELECT + " WHERE p.id = ?", (producto_id,))

    def obtener_por_codigo(self, codigo: str) -> Optional[dict]:
        return self._uno(_SELECT + " WHERE p.codigo = ?", (codigo,))

    def listar(
        self,
        texto: Optional[str] = None,
        solo_activos: bool = False,
        categoria_id: Optional[int] = None,
    ) -> list[dict]:
        condiciones: list[str] = []
        parametros: list = []
        if texto and texto.strip():
            patron = _patron_like(texto.strip())
            condiciones.append(
                f"(p.codigo LIKE ? ESCAPE '{_ESCAPE}' OR p.nombre LIKE ? ESCAPE '{_ESCAPE}')"
            )
            parametros += [patron, patron]
        if solo_activos:
            condiciones.append("p.activo = 1")
        if categoria_id is not None:
            condiciones.append("p.categoria_id = ?")
            parametros.append(categoria_id)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self._todos(_SELECT + where + " ORDER BY p.nombre, p.codigo", parametros)

    def alertas(self) -> list[dict]:
        """Productos activos con existencias <= stock mínimo (incluye agotados)."""
        return self._todos(
            _SELECT
            + """ WHERE p.activo = 1 AND p.stock_actual <= p.stock_minimo
                  ORDER BY (p.stock_actual = 0) DESC, p.stock_actual, p.nombre"""
        )

    def contar_activos(self) -> int:
        return self._contar("p.activo = 1")

    def contar_agotados(self) -> int:
        return self._contar("p.activo = 1 AND p.stock_actual = 0")

    def contar_stock_bajo(self) -> int:
        """Con existencias pero <= stock mínimo (no incluye agotados)."""
        return self._contar("p.activo = 1 AND p.stock_actual > 0 AND p.stock_actual <= p.stock_minimo")

    def _contar(self, condicion: str) -> int:
        fila = self._uno(f"SELECT COUNT(*) AS n FROM productos p WHERE {condicion}")
        return int(fila["n"])

    def tiene_historial(self, producto_id: int) -> bool:
        fila = self._uno(
            """SELECT EXISTS (SELECT 1 FROM movimientos_inventario WHERE producto_id = ?)
                    OR EXISTS (SELECT 1 FROM detalle_venta WHERE producto_id = ?) AS tiene""",
            (producto_id, producto_id),
        )
        return bool(fila["tiene"])
