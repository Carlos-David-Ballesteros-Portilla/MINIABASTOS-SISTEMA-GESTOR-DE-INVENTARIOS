"""Base de las pruebas: cada prueba usa una base de datos temporal e independiente.

Nunca se toca ``miniabastos.db`` (los datos reales del usuario).
"""
from __future__ import annotations

import os
import tempfile
import unittest

from controllers.inventario_controller import InventarioController
from controllers.producto_controller import ProductoController
from controllers.venta_controller import VentaController
from database.connection import get_connection
from database.initialization import inicializar_base_datos
from models.movimiento_model import MovimientoModel
from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from services.inventario_service import InventarioService
from services.venta_service import VentaService


class BaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._directorio = tempfile.TemporaryDirectory()
        self.addCleanup(self._directorio.cleanup)
        self.ruta_bd = os.path.join(self._directorio.name, "prueba.db")
        inicializar_base_datos(self.ruta_bd)
        self.conn = get_connection(self.ruta_bd)
        self.addCleanup(self._cerrar)

        self.productos_modelo = ProductoModel(self.conn)
        self.movimientos_modelo = MovimientoModel(self.conn)
        self.ventas_modelo = VentaModel(self.conn)
        self.producto_ctl = ProductoController(self.conn)
        self.inventario_ctl = InventarioController(self.conn)
        self.inventario = InventarioService(self.conn)
        self.ventas = VentaService(self.conn)
        self.categoria_id = self.producto_ctl.categoria_crear("General")

    def _cerrar(self) -> None:
        try:
            self.conn.close()
        except Exception:  # ya cerrada por la prueba
            pass

    # --- Ayudas -----------------------------------------------------------------------

    def crear_producto(self, codigo="P001", nombre="Producto", unidad="unidad",
                       precio="1000", minimo="0", stock=None) -> int:
        """Crea un producto; si se indica ``stock`` (texto) registra una entrada inicial."""
        producto_id = self.producto_ctl.producto_crear(
            codigo, nombre, "", unidad, self.categoria_id, precio, minimo
        )
        if stock is not None:
            self.inventario_ctl.registrar_entrada(producto_id, stock, "stock inicial de prueba")
        return producto_id

    def stock(self, producto_id: int) -> int:
        return self.productos_modelo.obtener(producto_id)["stock_actual"]

    def cantidad_movimientos(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM movimientos_inventario").fetchone()[0]

    def cantidad_ventas(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
