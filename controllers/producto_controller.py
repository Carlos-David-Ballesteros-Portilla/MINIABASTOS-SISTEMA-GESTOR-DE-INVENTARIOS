"""Controlador de productos y categorías: valida la entrada y delega en los modelos."""
from __future__ import annotations

import sqlite3
from typing import Optional

from models.categoria_model import CategoriaModel
from models.producto_model import ProductoModel
from services.inventario_service import clasificar_stock
from utils.errors import ErrorNoEncontrado, ErrorValidacion
from utils.validators import (
    parsear_cantidad,
    parsear_precio,
    texto_obligatorio,
    texto_opcional,
    validar_id,
)


class ProductoController:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.productos_modelo = ProductoModel(conn)
        self.categorias_modelo = CategoriaModel(conn)

    # --- Categorías ---------------------------------------------------------------

    def categorias(self) -> list[dict]:
        return self.categorias_modelo.listar()

    def categoria_crear(self, nombre, descripcion=None) -> int:
        return self.categorias_modelo.crear(
            texto_obligatorio(nombre, "El nombre de la categoría", 80),
            texto_opcional(descripcion, "La descripción"),
        )

    def categoria_actualizar(self, categoria_id, nombre, descripcion=None) -> None:
        categoria_id = validar_id(categoria_id, "una categoría")
        if not self.categorias_modelo.actualizar(
            categoria_id,
            texto_obligatorio(nombre, "El nombre de la categoría", 80),
            texto_opcional(descripcion, "La descripción"),
        ):
            raise ErrorNoEncontrado("La categoría no existe.")

    # --- Productos --------------------------------------------------------------------

    def productos(self, texto: Optional[str] = None, solo_activos: bool = False) -> list[dict]:
        filas = self.productos_modelo.listar(texto=texto, solo_activos=solo_activos)
        for fila in filas:
            fila["estado_stock"] = clasificar_stock(fila["stock_actual"], fila["stock_minimo"])
        return filas

    def producto_crear(
        self, codigo, nombre, descripcion, unidad, categoria_id, precio, stock_minimo
    ) -> int:
        datos = self._validar_datos(codigo, nombre, descripcion, unidad, categoria_id, precio, stock_minimo)
        return self.productos_modelo.crear(**datos)

    def producto_actualizar(
        self, producto_id, codigo, nombre, descripcion, unidad, categoria_id, precio, stock_minimo
    ) -> None:
        producto_id = validar_id(producto_id, "un producto")
        datos = self._validar_datos(codigo, nombre, descripcion, unidad, categoria_id, precio, stock_minimo)
        if not self.productos_modelo.actualizar(producto_id, **datos):
            raise ErrorNoEncontrado("El producto no existe.")

    def producto_desactivar(self, producto_id) -> None:
        self._cambiar_estado(producto_id, False)

    def producto_reactivar(self, producto_id) -> None:
        self._cambiar_estado(producto_id, True)

    # --- Interno ------------------------------------------------------------------------

    def _cambiar_estado(self, producto_id, activo: bool) -> None:
        producto_id = validar_id(producto_id, "un producto")
        if not self.productos_modelo.cambiar_estado(producto_id, activo):
            raise ErrorNoEncontrado("El producto no existe.")

    def _validar_datos(self, codigo, nombre, descripcion, unidad, categoria_id, precio, stock_minimo) -> dict:
        categoria_id = validar_id(categoria_id, "una categoría")
        if self.categorias_modelo.obtener(categoria_id) is None:
            raise ErrorValidacion("La categoría seleccionada no existe.")
        return {
            "codigo": texto_obligatorio(codigo, "El código", 40),
            "nombre": texto_obligatorio(nombre, "El nombre", 120),
            "descripcion": texto_opcional(descripcion, "La descripción"),
            "unidad_medida": texto_obligatorio(unidad, "La unidad de medida", 30),
            "categoria_id": categoria_id,
            "precio_venta": parsear_precio(precio, "El precio de venta", vacio_es_cero=True),
            "stock_minimo": parsear_cantidad(
                stock_minimo, "El stock mínimo", permitir_cero=True, vacio_es_cero=True
            ),
        }
