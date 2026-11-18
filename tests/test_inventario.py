"""Pruebas de inventario y movimientos."""
import sqlite3
import unittest

from tests.base import BaseTestCase
from utils.errors import ErrorStockInsuficiente, ErrorValidacion


class TestInventario(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.pid = self.crear_producto("INV001", nombre="Arroz", unidad="kg", minimo="2")

    def test_registrar_una_entrada(self):
        movimiento = self.inventario_ctl.registrar_entrada(self.pid, "10", "compra")
        self.assertEqual(self.stock(self.pid), 10000)
        self.assertEqual(movimiento["tipo"], "ENTRADA")
        self.assertEqual(movimiento["cantidad"], 10000)
        self.assertEqual((movimiento["stock_anterior"], movimiento["stock_posterior"]), (0, 10000))
        self.assertIsNone(movimiento["detalle_venta_id"])

    def test_registrar_un_ajuste_positivo(self):
        self.inventario_ctl.registrar_entrada(self.pid, "5")
        movimiento = self.inventario_ctl.registrar_ajuste(self.pid, "POSITIVO", "1,5", "conteo físico")
        self.assertEqual(self.stock(self.pid), 6500)
        self.assertEqual(movimiento["tipo"], "AJUSTE_POSITIVO")

    def test_registrar_un_ajuste_negativo(self):
        self.inventario_ctl.registrar_entrada(self.pid, "5")
        movimiento = self.inventario_ctl.registrar_ajuste(self.pid, "NEGATIVO", "0,75", "merma")
        self.assertEqual(self.stock(self.pid), 4250)
        self.assertEqual(movimiento["tipo"], "AJUSTE_NEGATIVO")
        self.assertEqual(movimiento["cantidad"], 750)  # la cantidad siempre es positiva

    def test_rechazar_ajuste_que_deja_stock_negativo(self):
        self.inventario_ctl.registrar_entrada(self.pid, "1")
        antes = self.cantidad_movimientos()
        with self.assertRaises(ErrorStockInsuficiente):
            self.inventario_ctl.registrar_ajuste(self.pid, "NEGATIVO", "1,001", "error")
        self.assertEqual(self.stock(self.pid), 1000)
        self.assertEqual(self.cantidad_movimientos(), antes)  # no se generó movimiento

    def test_ajustes_exigen_observacion(self):
        self.inventario_ctl.registrar_entrada(self.pid, "5")
        for direccion in ("POSITIVO", "NEGATIVO"):
            for observacion in ("", "   ", None):
                with self.assertRaises(ErrorValidacion):
                    self.inventario_ctl.registrar_ajuste(self.pid, direccion, "1", observacion)
        self.assertEqual(self.stock(self.pid), 5000)

    def test_rechazar_cantidades_invalidas(self):
        for cantidad in ("0", "-1", "abc", "1,2345", ""):
            with self.assertRaises(ErrorValidacion, msg=cantidad):
                self.inventario_ctl.registrar_entrada(self.pid, cantidad)
        for cantidad in (0, -5, 1.5, True):  # el servicio tampoco acepta float ni bool
            with self.assertRaises(ErrorValidacion, msg=str(cantidad)):
                self.inventario.registrar_entrada(self.pid, cantidad)
        self.assertEqual(self.cantidad_movimientos(), 0)

    def test_se_generan_movimientos_con_stock_anterior_y_posterior(self):
        self.inventario_ctl.registrar_entrada(self.pid, "10", "compra")
        self.inventario_ctl.registrar_ajuste(self.pid, "NEGATIVO", "2", "merma")
        self.inventario_ctl.registrar_ajuste(self.pid, "POSITIVO", "0,5", "hallazgo")
        movimientos = list(reversed(self.inventario_ctl.movimientos(self.pid)))  # cronológico
        self.assertEqual(
            [(m["tipo"], m["cantidad"], m["stock_anterior"], m["stock_posterior"]) for m in movimientos],
            [("ENTRADA", 10000, 0, 10000),
             ("AJUSTE_NEGATIVO", 2000, 10000, 8000),
             ("AJUSTE_POSITIVO", 500, 8000, 8500)],
        )

    def test_el_stock_coincide_con_las_operaciones(self):
        operaciones = [("E", "12,5"), ("N", "3"), ("P", "0,125"), ("E", "7"), ("N", "10,625")]
        esperado = 0
        for tipo, cantidad in operaciones:
            valor = int(round(float(cantidad.replace(",", ".")) * 1000))
            if tipo == "E":
                self.inventario_ctl.registrar_entrada(self.pid, cantidad)
                esperado += valor
            elif tipo == "P":
                self.inventario_ctl.registrar_ajuste(self.pid, "POSITIVO", cantidad, "ajuste")
                esperado += valor
            else:
                self.inventario_ctl.registrar_ajuste(self.pid, "NEGATIVO", cantidad, "ajuste")
                esperado -= valor
        self.assertEqual(self.stock(self.pid), esperado)
        self.assertEqual(self.inventario.verificar_coherencia(), [])
        suma = sum(
            m["cantidad"] if m["tipo"] in ("ENTRADA", "AJUSTE_POSITIVO") else -m["cantidad"]
            for m in self.inventario_ctl.movimientos(self.pid)
        )
        self.assertEqual(suma, self.stock(self.pid))

    def test_verificar_coherencia_detecta_stock_alterado_sin_movimiento(self):
        self.inventario_ctl.registrar_entrada(self.pid, "5")
        self.conn.execute("UPDATE productos SET stock_actual = 9999 WHERE id = ?", (self.pid,))
        discrepancias = self.inventario.verificar_coherencia()
        self.assertEqual(len(discrepancias), 1)
        self.assertEqual(discrepancias[0]["stock_segun_movimientos"], 5000)

    def test_movimientos_no_se_pueden_modificar_ni_borrar(self):
        movimiento = self.inventario_ctl.registrar_entrada(self.pid, "5")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE movimientos_inventario SET cantidad = 1 WHERE id = ?", (movimiento["id"],))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM movimientos_inventario WHERE id = ?", (movimiento["id"],))
        self.assertEqual(self.cantidad_movimientos(), 1)

    def test_una_salida_requiere_venta_y_el_detalle_debe_ser_del_mismo_producto(self):
        otro = self.crear_producto("INV002", stock="5")
        self.inventario_ctl.registrar_entrada(self.pid, "5")
        venta = self.ventas.confirmar_venta([{"producto_id": self.pid, "cantidad": 1000, "precio_unitario": 100}])
        detalle_id = venta["detalles"][0]["id"]
        insertar = (
            "INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, stock_anterior, "
            "stock_posterior, detalle_venta_id, fecha) VALUES (?, ?, 1000, 5000, ?, ?, '2026-01-01 00:00:00')"
        )
        with self.assertRaises(sqlite3.IntegrityError):  # SALIDA sin venta
            self.conn.execute(insertar, (self.pid, "SALIDA", 4000, None))
        with self.assertRaises(sqlite3.IntegrityError):  # detalle de otro producto
            self.conn.execute(insertar, (otro, "SALIDA", 4000, detalle_id))
        with self.assertRaises(sqlite3.IntegrityError):  # un ajuste no puede venir de una venta
            self.conn.execute(
                "INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, stock_anterior, "
                "stock_posterior, detalle_venta_id, fecha, observacion) "
                "VALUES (?, 'AJUSTE_NEGATIVO', 1000, 5000, 4000, ?, '2026-01-01 00:00:00', 'x')",
                (self.pid, detalle_id),
            )

    def test_alertas_incluyen_agotados_y_stock_bajo(self):
        bajo = self.crear_producto("BAJ001", nombre="Bajo", minimo="5", stock="3")
        normal = self.crear_producto("NOR001", nombre="Normal", minimo="5", stock="20")
        alertas = {a["id"]: a["estado_stock"] for a in self.inventario.alertas()}
        self.assertEqual(alertas[self.pid], "AGOTADO")  # stock 0
        self.assertEqual(alertas[bajo], "BAJO")
        self.assertNotIn(normal, alertas)
        igual_al_minimo = self.crear_producto("MIN001", minimo="4", stock="4")
        self.assertEqual({a["id"]: a["estado_stock"] for a in self.inventario.alertas()}[igual_al_minimo], "BAJO")


if __name__ == "__main__":
    unittest.main()
