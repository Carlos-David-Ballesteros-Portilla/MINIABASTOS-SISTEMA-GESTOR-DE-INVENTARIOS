"""Datos de demostración OPCIONALES, separados de los datos reales.

Se cargan solo con ``python main.py --demo`` (base ``miniabastos_demo.db``) o
ejecutando este archivo directamente. Nunca se cargan en ``miniabastos.db``
por defecto. Los datos se crean usando los mismos servicios que la aplicación,
por lo que respetan todas las reglas de integridad.
"""
from __future__ import annotations

import sqlite3
import sys

from controllers.producto_controller import ProductoController
from database.connection import RAIZ_PROYECTO, get_connection
from database.initialization import inicializar_base_datos
from models.producto_model import ProductoModel
from services.inventario_service import InventarioService
from services.venta_service import VentaService

# (código, nombre, categoría, unidad, precio COP, stock mínimo, stock inicial)
PRODUCTOS_DEMO = (
    ("ARR001", "Arroz", "Granos", "kg", "3200", "5", "40"),
    ("FRI001", "Fríjol", "Granos", "kg", "6500", "3", "20,5"),
    ("LEC001", "Leche entera 1 L", "Lácteos", "unidad", "4200", "10", "24"),
    ("HUE001", "Huevos (unidad)", "Lácteos", "unidad", "700", "30", "90"),
    ("GAS001", "Gaseosa 1,5 L", "Bebidas", "unidad", "5500", "6", "5"),
    ("JAB001", "Jabón de barra", "Aseo", "unidad", "2800", "8", "0"),
)


def cargar_datos_demo(conn: sqlite3.Connection) -> bool:
    """Carga datos de ejemplo si la base está vacía. Devuelve True si cargó algo."""
    if ProductoModel(conn).contar_activos() or ProductoModel(conn).listar():
        return False

    productos = ProductoController(conn)
    inventario = InventarioService(conn)
    ventas = VentaService(conn)

    categorias = {nombre: productos.categoria_crear(nombre) for nombre in ("Granos", "Lácteos", "Bebidas", "Aseo")}
    from utils.validators import parsear_cantidad

    ids = {}
    for codigo, nombre, categoria, unidad, precio, minimo, inicial in PRODUCTOS_DEMO:
        ids[codigo] = productos.producto_crear(codigo, nombre, "", unidad, categorias[categoria], precio, minimo)
        cantidad = parsear_cantidad(inicial, permitir_cero=True)
        if cantidad:
            inventario.registrar_entrada(ids[codigo], cantidad, "Inventario inicial de demostración")

    ventas.confirmar_venta(
        [
            {"producto_id": ids["ARR001"], "cantidad": 1500, "precio_unitario": 3200},
            {"producto_id": ids["LEC001"], "cantidad": 2000, "precio_unitario": 4200},
        ],
        "Venta de demostración",
    )
    venta_anulada = ventas.confirmar_venta(
        [{"producto_id": ids["GAS001"], "cantidad": 1000, "precio_unitario": 5500}],
        "Venta de demostración (anulada)",
    )
    ventas.anular_venta(venta_anulada["id"])
    return True


if __name__ == "__main__":
    ruta = RAIZ_PROYECTO / "miniabastos_demo.db"
    inicializar_base_datos(ruta)
    conexion = get_connection(ruta)
    try:
        cargado = cargar_datos_demo(conexion)
    finally:
        conexion.close()
    print(f"Datos de demostración {'cargados en' if cargado else 'ya existentes en'} {ruta}")
    sys.exit(0)
