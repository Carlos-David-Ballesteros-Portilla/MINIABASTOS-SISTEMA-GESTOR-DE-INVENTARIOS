"""Pruebas de persistencia: los datos sobreviven al cierre y reapertura de conexiones."""
import os
import unittest

from controllers.dashboard_controller import DashboardController
from controllers.inventario_controller import InventarioController
from controllers.producto_controller import ProductoController
from database.connection import get_connection
from database.initialization import inicializar_base_datos
from models.producto_model import ProductoModel
from models.venta_model import VentaModel
from services.venta_service import VentaService
from tests.base import BaseTestCase


class TestPersistencia(BaseTestCase):
    def test_los_registros_siguen_disponibles_tras_cerrar_y_reabrir(self):
        producto_id = self.crear_producto("PER001", "Panela", "kg", "4500", "1", stock="8,5")
        venta = self.ventas.confirmar_venta(
            [{"producto_id": producto_id, "cantidad": 1500, "precio_unitario": 4500}], "persistente"
        )
        venta_anulada = self.ventas.confirmar_venta(
            [{"producto_id": producto_id, "cantidad": 500, "precio_unitario": 4500}]
        )
        self.ventas.anular_venta(venta_anulada["id"])
        self.conn.close()

        nueva = get_connection(self.ruta_bd)
        self.addCleanup(nueva.close)
        producto = ProductoModel(nueva).obtener(producto_id)
        self.assertEqual(producto["codigo"], "PER001")
        self.assertEqual(producto["stock_actual"], 7000)  # 8,5 - 1,5
        reabierta = VentaService(nueva).obtener_venta(venta["id"])
        self.assertEqual(reabierta["total"], 6750)
        self.assertEqual(reabierta["observaciones"], "persistente")
        self.assertEqual(VentaModel(nueva).obtener(venta_anulada["id"])["estado"], "ANULADA")
        self.assertEqual(len(InventarioController(nueva).movimientos(producto_id)), 4)  # entrada, 2 salidas, reversión

    def test_cada_conexion_nueva_activa_las_claves_foraneas(self):
        self.conn.close()
        nueva = get_connection(self.ruta_bd)
        self.addCleanup(nueva.close)
        self.assertEqual(nueva.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_inicializar_dos_veces_no_borra_datos(self):
        self.crear_producto("PER002", stock="3")
        inicializar_base_datos(self.ruta_bd)  # equivale a arrancar la aplicación de nuevo
        self.assertEqual(len(self.productos_modelo.listar()), 1)
        self.assertEqual(self.cantidad_movimientos(), 1)

    def test_la_base_se_crea_automaticamente_en_la_primera_ejecucion(self):
        ruta = os.path.join(self._directorio.name, "carpeta", "nueva.db")
        self.assertFalse(os.path.exists(ruta))
        inicializar_base_datos(ruta)
        self.assertTrue(os.path.exists(ruta))
        conn = get_connection(ruta)
        self.addCleanup(conn.close)
        tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertTrue(
            {"categorias", "productos", "ventas", "detalle_venta", "movimientos_inventario"} <= tablas
        )

    def test_el_panel_refleja_las_existencias_reales(self):
        agotado = self.crear_producto("AGO001", minimo="2")
        bajo = self.crear_producto("BAJ001", minimo="5", stock="3")
        self.crear_producto("OK0001", minimo="1", stock="10")
        inactivo = self.crear_producto("INA001", minimo="5")
        self.producto_ctl.producto_desactivar(inactivo)  # los inactivos no cuentan
        resumen = DashboardController(self.conn).resumen()
        self.assertEqual(resumen["productos_activos"], 3)
        self.assertEqual(resumen["agotados"], 1)
        self.assertEqual(resumen["stock_bajo"], 1)
        self.assertEqual(len(resumen["ultimos_movimientos"]), 2)
        self.assertIsNotNone(agotado)
        self.assertIsNotNone(bajo)


if __name__ == "__main__":
    unittest.main()
