"""Pruebas de productos y categorías."""
import sqlite3
import unittest

from tests.base import BaseTestCase
from utils.errors import ErrorDuplicado, ErrorValidacion


class TestProductos(BaseTestCase):
    def test_registrar_producto_correctamente(self):
        producto_id = self.producto_ctl.producto_crear(
            "ARR001", "Arroz", "Arroz blanco", "kg", self.categoria_id, "$3.200", "2,5"
        )
        producto = self.productos_modelo.obtener(producto_id)
        self.assertEqual(producto["codigo"], "ARR001")
        self.assertEqual(producto["nombre"], "Arroz")
        self.assertEqual(producto["precio_venta"], 3200)
        self.assertEqual(producto["stock_minimo"], 2500)  # 2,5 kg escalado x1000
        self.assertEqual(producto["stock_actual"], 0)
        self.assertEqual(producto["activo"], 1)

    def test_rechazar_codigo_duplicado(self):
        self.crear_producto("DUP001")
        with self.assertRaises(ErrorDuplicado):
            self.crear_producto("DUP001", nombre="Otro")
        with self.assertRaises(ErrorDuplicado):  # sin distinguir mayúsculas
            self.crear_producto("dup001", nombre="Otro")
        self.assertEqual(len(self.productos_modelo.listar()), 1)

    def test_rechazar_precio_negativo(self):
        with self.assertRaises(ErrorValidacion):
            self.crear_producto("NEG001", precio="-100")
        self.assertEqual(self.productos_modelo.listar(), [])

    def test_rechazar_stock_minimo_negativo(self):
        with self.assertRaises(ErrorValidacion):
            self.crear_producto("NEG002", minimo="-1")
        self.assertEqual(self.productos_modelo.listar(), [])

    def test_base_de_datos_rechaza_valores_negativos_aunque_se_omita_el_controlador(self):
        sql = (
            "INSERT INTO productos (codigo, nombre, unidad_medida, categoria_id, "
            "precio_venta, stock_actual, stock_minimo) VALUES (?, 'x', 'unidad', ?, ?, ?, ?)"
        )
        for parametros in (("X1", self.categoria_id, -1, 0, 0),
                           ("X2", self.categoria_id, 0, -1, 0),
                           ("X3", self.categoria_id, 0, 0, -1)):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql, parametros)

    def test_rechazar_precio_con_decimales_o_texto_invalido(self):
        for texto in ("12,5", "abc", "2.5"):
            with self.assertRaises(ErrorValidacion, msg=texto):
                self.crear_producto("PRE001", precio=texto)

    def test_modificar_producto_conserva_stock(self):
        producto_id = self.crear_producto("MOD001", stock="4")
        self.producto_ctl.producto_actualizar(
            producto_id, "MOD001", "Nombre nuevo", "", "unidad", self.categoria_id, "1500", "1"
        )
        producto = self.productos_modelo.obtener(producto_id)
        self.assertEqual(producto["nombre"], "Nombre nuevo")
        self.assertEqual(producto["precio_venta"], 1500)
        self.assertEqual(producto["stock_actual"], 4000)

    def test_desactivar_y_reactivar(self):
        producto_id = self.crear_producto("ACT001")
        self.producto_ctl.producto_desactivar(producto_id)
        self.assertEqual(self.productos_modelo.obtener(producto_id)["activo"], 0)
        self.assertEqual(self.producto_ctl.productos(solo_activos=True), [])
        self.producto_ctl.producto_reactivar(producto_id)
        self.assertEqual(self.productos_modelo.obtener(producto_id)["activo"], 1)

    def test_producto_con_historial_no_se_puede_eliminar(self):
        producto_id = self.crear_producto("HIS001", stock="1")
        self.assertTrue(self.productos_modelo.tiene_historial(producto_id))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM productos WHERE id = ?", (producto_id,))

    def test_categorias_sin_nombres_duplicados_y_modificables(self):
        with self.assertRaises(ErrorDuplicado):
            self.producto_ctl.categoria_crear("general")  # ya existe "General"
        otra = self.producto_ctl.categoria_crear("Bebidas", "Líquidos")
        self.producto_ctl.categoria_actualizar(otra, "Bebidas frías", "Refrescos")
        self.assertEqual(self.producto_ctl.categorias()[0]["nombre"], "Bebidas frías")
        with self.assertRaises(ErrorDuplicado):
            self.producto_ctl.categoria_actualizar(otra, "General")

    def test_busqueda_por_codigo_o_nombre_es_literal(self):
        self.crear_producto("LEC001", nombre="Leche 100% entera")
        self.crear_producto("ARR001", nombre="Arroz")
        self.assertEqual([p["codigo"] for p in self.productos_modelo.listar("leche")], ["LEC001"])
        self.assertEqual([p["codigo"] for p in self.productos_modelo.listar("arr0")], ["ARR001"])  # subcadena
        # "_" se busca literalmente: si fuera comodín, "arr_01" coincidiría con "ARR001".
        self.assertEqual(self.productos_modelo.listar("arr_01"), [])
        self.assertEqual([p["codigo"] for p in self.productos_modelo.listar("100%")], ["LEC001"])
        # "%" se busca literalmente: no actúa como comodín que devuelva todo.
        self.assertEqual([p["codigo"] for p in self.productos_modelo.listar("%")], ["LEC001"])


if __name__ == "__main__":
    unittest.main()
