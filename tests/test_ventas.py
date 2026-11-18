"""Pruebas de ventas y anulaciones."""
import unittest
from unittest.mock import patch

from controllers.venta_controller import VentaController
from services.inventario_service import InventarioService
from tests.base import BaseTestCase
from utils.calculos import calcular_subtotal, calcular_total
from utils.errors import (
    ErrorEstadoInvalido,
    ErrorNegocio,
    ErrorStockInsuficiente,
    ErrorValidacion,
)


class TestCalculos(unittest.TestCase):
    def test_subtotal_con_cantidades_fraccionarias(self):
        self.assertEqual(calcular_subtotal(1000, 2500), 2500)   # 1 unidad
        self.assertEqual(calcular_subtotal(500, 2500), 1250)    # 0,5 kg
        self.assertEqual(calcular_subtotal(1250, 3300), 4125)   # 1,250 kg
        self.assertEqual(calcular_subtotal(2750, 4000), 11000)  # 2,750 L

    def test_redondeo_half_up_a_pesos_enteros(self):
        self.assertEqual(calcular_subtotal(500, 25), 13)   # 12,5 -> 13
        self.assertEqual(calcular_subtotal(500, 24), 12)   # 12,0
        self.assertEqual(calcular_subtotal(1, 1499), 1)    # 1,499 -> 1
        self.assertEqual(calcular_subtotal(1, 1500), 2)    # 1,5 -> 2
        self.assertEqual(calcular_subtotal(333, 100), 33)  # 33,3 -> 33

    def test_el_total_suma_subtotales_ya_redondeados(self):
        subtotales = [calcular_subtotal(500, 25), calcular_subtotal(500, 25)]
        self.assertEqual(subtotales, [13, 13])
        self.assertEqual(calcular_total(subtotales), 26)  # no 25 (que sería redondear 12,5+12,5)


class TestVentas(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.arroz = self.crear_producto("ARR001", "Arroz", "kg", "2500", "1", stock="10")
        self.leche = self.crear_producto("LEC001", "Leche", "unidad", "4200", "2", stock="5")

    def item(self, producto_id, cantidad, precio):
        return {"producto_id": producto_id, "cantidad": cantidad, "precio_unitario": precio}

    def test_registrar_venta_con_un_producto(self):
        venta = self.ventas.confirmar_venta([self.item(self.leche, 2000, 4200)])
        self.assertEqual(venta["estado"], "CONFIRMADA")
        self.assertEqual(venta["total"], 8400)
        self.assertEqual(len(venta["detalles"]), 1)
        self.assertEqual(venta["detalles"][0]["cantidad"], 2000)

    def test_registrar_venta_con_varios_productos_y_calcular_subtotales_y_total(self):
        venta = self.ventas.confirmar_venta(
            [self.item(self.arroz, 1250, 2500), self.item(self.leche, 2000, 4200)], "mostrador"
        )
        subtotales = {d["codigo"]: d["subtotal"] for d in venta["detalles"]}
        self.assertEqual(subtotales, {"ARR001": 3125, "LEC001": 8400})
        self.assertEqual(venta["total"], 11525)
        self.assertEqual(venta["observaciones"], "mostrador")

    def test_cantidades_fraccionarias(self):
        venta = self.ventas.confirmar_venta([self.item(self.arroz, 500, 2500)])  # 0,5 kg
        self.assertEqual(venta["total"], 1250)
        self.assertEqual(self.stock(self.arroz), 9500)
        venta = self.ventas.confirmar_venta([self.item(self.arroz, 1, 2500)])  # 0,001 kg -> 2,5 -> 3
        self.assertEqual(venta["total"], 3)
        self.assertEqual(self.stock(self.arroz), 9499)

    def test_comprueba_actualizacion_de_existencias(self):
        self.ventas.confirmar_venta([self.item(self.arroz, 1250, 2500), self.item(self.leche, 2000, 4200)])
        self.assertEqual(self.stock(self.arroz), 8750)
        self.assertEqual(self.stock(self.leche), 3000)
        self.assertEqual(self.inventario.verificar_coherencia(), [])

    def test_genera_un_movimiento_salida_por_detalle(self):
        venta = self.ventas.confirmar_venta([self.item(self.arroz, 1250, 2500), self.item(self.leche, 2000, 4200)])
        salidas = [m for m in self.movimientos_modelo.listar() if m["tipo"] == "SALIDA"]
        self.assertEqual(len(salidas), 2)
        detalles = {d["id"]: d for d in venta["detalles"]}
        for salida in salidas:
            detalle = detalles[salida["detalle_venta_id"]]
            self.assertEqual(salida["producto_id"], detalle["producto_id"])
            self.assertEqual(salida["cantidad"], detalle["cantidad"])
            self.assertEqual(salida["venta_id"], venta["id"])
            self.assertEqual(salida["stock_anterior"] - salida["cantidad"], salida["stock_posterior"])

    def test_rechazar_venta_sin_stock_suficiente_sin_efectos_parciales(self):
        antes_arroz, antes_leche = self.stock(self.arroz), self.stock(self.leche)
        movimientos_antes = self.cantidad_movimientos()
        # El primer producto alcanza; el segundo no: no debe quedar nada a medias.
        with self.assertRaises(ErrorStockInsuficiente) as contexto:
            self.ventas.confirmar_venta([self.item(self.arroz, 1000, 2500), self.item(self.leche, 5001, 4200)])
        self.assertIn("Leche", str(contexto.exception))
        self.assertEqual((self.stock(self.arroz), self.stock(self.leche)), (antes_arroz, antes_leche))
        self.assertEqual(self.cantidad_ventas(), 0)
        self.assertEqual(self.cantidad_movimientos(), movimientos_antes)

    def test_se_puede_vender_exactamente_todo_el_stock(self):
        self.ventas.confirmar_venta([self.item(self.leche, 5000, 4200)])
        self.assertEqual(self.stock(self.leche), 0)

    def test_rechazar_ventas_vacias(self):
        for items in ([], None):
            with self.assertRaises(ErrorValidacion):
                self.ventas.confirmar_venta(items)
        self.assertEqual(self.cantidad_ventas(), 0)

    def test_rechazar_cantidades_no_positivas_y_precios_negativos(self):
        for cantidad in (0, -1000):
            with self.assertRaises(ErrorValidacion):
                self.ventas.confirmar_venta([self.item(self.arroz, cantidad, 2500)])
        with self.assertRaises(ErrorValidacion):
            self.ventas.confirmar_venta([self.item(self.arroz, 1000, -1)])
        self.assertEqual(self.cantidad_ventas(), 0)

    def test_rechazar_productos_desactivados(self):
        self.producto_ctl.producto_desactivar(self.arroz)
        with self.assertRaises(ErrorValidacion):
            self.ventas.confirmar_venta([self.item(self.arroz, 1000, 2500)])
        controlador = VentaController(self.conn)
        self.assertNotIn(self.arroz, [p["id"] for p in controlador.buscar_productos("")])
        with self.assertRaises(ErrorValidacion):
            controlador.agregar_al_carrito(self.arroz, "1")
        self.assertEqual(self.stock(self.arroz), 10000)

    def test_el_precio_aplicado_se_conserva_aunque_cambie_el_precio_del_producto(self):
        venta = self.ventas.confirmar_venta([self.item(self.arroz, 2000, 2400)])  # precio modificado en la venta
        self.producto_ctl.producto_actualizar(
            self.arroz, "ARR001", "Arroz", "", "kg", self.categoria_id, "9999", "1"
        )
        detalle = self.ventas_modelo.obtener_detalles(venta["id"])[0]
        self.assertEqual(detalle["precio_unitario"], 2400)
        self.assertEqual(detalle["subtotal"], 4800)

    def test_producto_repetido_en_una_venta_acumula_cantidad_en_un_solo_detalle(self):
        venta = self.ventas.confirmar_venta([self.item(self.arroz, 1000, 2500), self.item(self.arroz, 500, 2500)])
        self.assertEqual(len(venta["detalles"]), 1)
        self.assertEqual(venta["detalles"][0]["cantidad"], 1500)
        self.assertEqual(venta["total"], 3750)
        with self.assertRaises(ErrorValidacion):  # mismo producto con precios distintos: ambiguo
            self.ventas.confirmar_venta([self.item(self.arroz, 1000, 2500), self.item(self.arroz, 500, 2600)])

    def test_carrito_acumula_y_confirma(self):
        carrito = VentaController(self.conn)
        carrito.agregar_al_carrito(self.arroz, "1,25")
        resumen = carrito.agregar_al_carrito(self.arroz, "0,5", "2.600")
        self.assertEqual(len(resumen["lineas"]), 1)
        self.assertEqual(resumen["lineas"][0]["cantidad"], 1750)
        self.assertEqual(resumen["total"], 4550)  # 1,75 kg x 2.600
        venta = carrito.confirmar_venta("con carrito")
        self.assertEqual(venta["total"], 4550)
        self.assertEqual(carrito.obtener_carrito()["lineas"], [])
        self.assertEqual(self.stock(self.arroz), 8250)

    def test_carrito_se_conserva_si_la_confirmacion_falla(self):
        carrito = VentaController(self.conn)
        carrito.agregar_al_carrito(self.leche, "6")  # hay 5
        with self.assertRaises(ErrorStockInsuficiente):
            carrito.confirmar_venta()
        self.assertEqual(len(carrito.obtener_carrito()["lineas"]), 1)
        with self.assertRaises(ErrorValidacion):
            VentaController(self.conn).confirmar_venta()  # carrito vacío

    def test_total_del_dia_solo_cuenta_ventas_confirmadas(self):
        fecha = "2026-03-10 10:00:00"
        a = self.ventas.confirmar_venta([self.item(self.arroz, 1000, 2500)], fecha=fecha)
        b = self.ventas.confirmar_venta([self.item(self.leche, 1000, 4200)], fecha="2026-03-10 18:30:00")
        self.ventas.anular_venta(b["id"])
        self.assertEqual(self.ventas_modelo.total_confirmado_del_dia("2026-03-10"), a["total"])
        fila = self.ventas_modelo.totales_por_dia("2026-03-10", "2026-03-10")[0]
        self.assertEqual((fila["ventas_confirmadas"], fila["total_confirmado"]), (1, 2500))
        self.assertEqual((fila["ventas_anuladas"], fila["total_anulado"]), (1, 4200))


class TestAnulacion(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.arroz = self.crear_producto("ARR001", "Arroz", "kg", "2500", "1", stock="10")
        self.leche = self.crear_producto("LEC001", "Leche", "unidad", "4200", "2", stock="5")
        self.venta = self.ventas.confirmar_venta(
            [
                {"producto_id": self.arroz, "cantidad": 1250, "precio_unitario": 2500},
                {"producto_id": self.leche, "cantidad": 2000, "precio_unitario": 4200},
            ]
        )

    def test_anular_una_venta(self):
        anulada = self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(anulada["estado"], "ANULADA")
        self.assertEqual(self.ventas_modelo.obtener(self.venta["id"])["estado"], "ANULADA")

    def test_restaura_existencias(self):
        self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(self.stock(self.arroz), 10000)
        self.assertEqual(self.stock(self.leche), 5000)
        self.assertEqual(self.inventario.verificar_coherencia(), [])

    def test_conserva_el_historial_y_registra_reversiones_como_entradas(self):
        antes = self.cantidad_movimientos()
        self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(self.cantidad_movimientos(), antes + 2)  # nada se borra: solo se agregan
        movimientos = self.movimientos_modelo.listar()
        salidas = [m for m in movimientos if m["tipo"] == "SALIDA"]
        reversiones = [m for m in movimientos if m["tipo"] == "ENTRADA" and m["detalle_venta_id"]]
        self.assertEqual(len(salidas), 2)  # los originales siguen ahí
        self.assertEqual(len(reversiones), 2)
        self.assertEqual({m["detalle_venta_id"] for m in salidas}, {m["detalle_venta_id"] for m in reversiones})
        # La venta y su detalle se conservan para consulta.
        self.assertEqual(len(self.ventas.obtener_venta(self.venta["id"])["detalles"]), 2)
        self.assertEqual(self.ventas_modelo.obtener(self.venta["id"])["total"], 11525)

    def test_rechazar_segunda_anulacion_sin_afectar_el_inventario(self):
        self.ventas.anular_venta(self.venta["id"])
        movimientos = self.cantidad_movimientos()
        with self.assertRaises(ErrorEstadoInvalido):
            self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(self.stock(self.arroz), 10000)  # no se sumó dos veces
        self.assertEqual(self.stock(self.leche), 5000)
        self.assertEqual(self.cantidad_movimientos(), movimientos)

    def test_rechazar_anular_venta_inexistente(self):
        with self.assertRaises(ErrorNegocio):
            self.ventas.anular_venta(9999)

    def test_una_anulacion_fallida_no_modifica_parcialmente_el_inventario(self):
        stock_arroz, stock_leche = self.stock(self.arroz), self.stock(self.leche)
        movimientos = self.cantidad_movimientos()
        original = InventarioService.registrar_reversion_venta
        llamadas = {"n": 0}

        def falla_en_la_segunda(servicio, *args, **kwargs):
            llamadas["n"] += 1
            if llamadas["n"] == 2:
                raise RuntimeError("fallo simulado a mitad de la anulación")
            return original(servicio, *args, **kwargs)

        with patch.object(InventarioService, "registrar_reversion_venta", falla_en_la_segunda):
            with self.assertRaises(RuntimeError):
                self.ventas.anular_venta(self.venta["id"])

        self.assertEqual(llamadas["n"], 2)  # la primera reversión sí se ejecutó antes del fallo...
        self.assertEqual((self.stock(self.arroz), self.stock(self.leche)), (stock_arroz, stock_leche))  # ...y se revirtió
        self.assertEqual(self.cantidad_movimientos(), movimientos)
        self.assertEqual(self.ventas_modelo.obtener(self.venta["id"])["estado"], "CONFIRMADA")
        self.assertFalse(self.conn.in_transaction)
        # Tras el fallo, la anulación real todavía puede hacerse con normalidad.
        self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(self.stock(self.arroz), 10000)

    def test_una_venta_anulada_no_puede_volver_a_confirmarse(self):
        import sqlite3

        self.ventas.anular_venta(self.venta["id"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE ventas SET estado = 'CONFIRMADA' WHERE id = ?", (self.venta["id"],))

    def test_anular_venta_de_producto_desactivado_restaura_su_stock(self):
        self.producto_ctl.producto_desactivar(self.arroz)
        self.ventas.anular_venta(self.venta["id"])
        self.assertEqual(self.stock(self.arroz), 10000)


if __name__ == "__main__":
    unittest.main()
