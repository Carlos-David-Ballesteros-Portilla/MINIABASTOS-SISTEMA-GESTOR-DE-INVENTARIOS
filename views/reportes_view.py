"""Vista de reportes de consulta."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from utils.formatters import formatear_moneda
from views.widgets import (
    CENTRO,
    COLUMNAS_DETALLE_VENTA,
    COLUMNAS_MOVIMIENTOS,
    COLUMNAS_PRODUCTOS_STOCK,
    COLUMNAS_VENTAS,
    DER,
    FUENTE_SUBTITULO,
    IZQ,
    PAD,
    BarraFechas,
    crear_tabla,
    crear_titulo,
    fila_detalle_venta,
    fila_movimiento,
    fila_producto_stock,
    fila_venta,
    id_seleccionado,
    llenar_tabla,
    manejar_errores,
)

TODOS = "Todos los productos"
FILTROS_ESTADO = (("Todas", None), ("Confirmadas", "CONFIRMADA"), ("Anuladas", "ANULADA"))
COLUMNAS_DIARIAS = (
    ("dia", "Día", 110, IZQ),
    ("n_confirmadas", "Ventas confirmadas", 140, CENTRO),
    ("total", "Total confirmado", 140, DER),
    ("n_anuladas", "Ventas anuladas", 130, CENTRO),
    ("anulado", "Valor anulado (no suma)", 170, DER),
)


class ReportesView(ttk.Frame):
    def __init__(self, padre, controladores) -> None:
        super().__init__(padre, padding=PAD * 2)
        self.controlador = controladores.reporte
        self._productos: dict[str, int] = {}

        crear_titulo(self, "Reportes")
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True)
        self._construir_inventario(pestanas)
        self._construir_movimientos(pestanas)
        self._construir_ventas(pestanas)
        self._construir_totales(pestanas)

    # --- Inventario actual -----------------------------------------------------------------

    def _construir_inventario(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Inventario actual")
        ttk.Button(marco, text="Actualizar", command=self.cargar_inventario).pack(anchor="w")
        tabla_marco, self.tabla_inventario = crear_tabla(marco, COLUMNAS_PRODUCTOS_STOCK, altura=18)
        tabla_marco.pack(fill="both", expand=True, pady=PAD)

    @manejar_errores
    def cargar_inventario(self) -> None:
        llenar_tabla(self.tabla_inventario, [fila_producto_stock(p) for p in self.controlador.inventario_actual()])

    # --- Movimientos (por producto y/o rango de fechas) -------------------------------------------

    def _construir_movimientos(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Movimientos")
        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        ttk.Label(barra, text="Producto:").pack(side="left")
        self.var_producto = tk.StringVar(value=TODOS)
        self.combo_producto = ttk.Combobox(barra, textvariable=self.var_producto, state="readonly", width=32)
        self.combo_producto.pack(side="left", padx=PAD)
        self.fechas_movimientos = BarraFechas(barra)
        self.fechas_movimientos.pack(side="left")
        ttk.Button(barra, text="Consultar", command=self.cargar_movimientos).pack(side="left")
        tabla_marco, self.tabla_movimientos = crear_tabla(marco, COLUMNAS_MOVIMIENTOS, altura=18)
        tabla_marco.pack(fill="both", expand=True, pady=PAD)

    @manejar_errores
    def cargar_movimientos(self) -> None:
        desde, hasta = self.fechas_movimientos.valores()
        producto_id = self._productos.get(self.var_producto.get())
        movimientos = self.controlador.movimientos(producto_id, desde, hasta)
        llenar_tabla(self.tabla_movimientos, [fila_movimiento(m) for m in movimientos])

    # --- Historial y detalle de ventas ---------------------------------------------------------------

    def _construir_ventas(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Historial de ventas")
        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        self.fechas_ventas = BarraFechas(barra)
        self.fechas_ventas.pack(side="left")
        ttk.Label(barra, text="Estado:").pack(side="left")
        self.var_estado = tk.StringVar(value=FILTROS_ESTADO[0][0])
        ttk.Combobox(
            barra, textvariable=self.var_estado, state="readonly", width=14,
            values=[f[0] for f in FILTROS_ESTADO],
        ).pack(side="left", padx=PAD)
        ttk.Button(barra, text="Consultar", command=self.cargar_ventas).pack(side="left")

        marco_ventas, self.tabla_ventas = crear_tabla(marco, COLUMNAS_VENTAS, altura=9)
        marco_ventas.pack(fill="both", expand=True, pady=PAD)
        self.tabla_ventas.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalle())
        ttk.Label(marco, text="Detalle de la venta seleccionada", font=FUENTE_SUBTITULO).pack(anchor="w")
        marco_detalle, self.tabla_detalle = crear_tabla(marco, COLUMNAS_DETALLE_VENTA, altura=6)
        marco_detalle.pack(fill="both", expand=True, pady=(4, 0))

    @manejar_errores
    def cargar_ventas(self) -> None:
        desde, hasta = self.fechas_ventas.valores()
        estado = dict(FILTROS_ESTADO)[self.var_estado.get()]
        ventas = self.controlador.historial_ventas(desde, hasta, estado)
        llenar_tabla(self.tabla_ventas, [fila_venta(v) for v in ventas])
        llenar_tabla(self.tabla_detalle, [])

    @manejar_errores
    def _mostrar_detalle(self) -> None:
        venta_id: Optional[int] = id_seleccionado(self.tabla_ventas)
        if venta_id is None:
            return
        venta = self.controlador.detalle_venta(venta_id)
        llenar_tabla(self.tabla_detalle, [fila_detalle_venta(d) for d in venta["detalles"]])

    # --- Total de ventas por día ------------------------------------------------------------------------

    def _construir_totales(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Ventas por día")
        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        self.fechas_totales = BarraFechas(barra)
        self.fechas_totales.pack(side="left")
        ttk.Button(barra, text="Consultar", command=self.cargar_totales).pack(side="left")
        tabla_marco, self.tabla_totales = crear_tabla(marco, COLUMNAS_DIARIAS, altura=16)
        tabla_marco.pack(fill="both", expand=True, pady=PAD)
        self.etiqueta_total = ttk.Label(marco, text="", font=FUENTE_SUBTITULO)
        self.etiqueta_total.pack(anchor="e")
        ttk.Label(
            marco, text="El total considera únicamente las ventas confirmadas.", foreground="#666666"
        ).pack(anchor="e")

    @manejar_errores
    def cargar_totales(self) -> None:
        desde, hasta = self.fechas_totales.valores()
        reporte = self.controlador.totales_por_dia(desde, hasta)
        llenar_tabla(
            self.tabla_totales,
            [
                (None, (f["dia"], f["ventas_confirmadas"], formatear_moneda(f["total_confirmado"]),
                        f["ventas_anuladas"], formatear_moneda(f["total_anulado"])), ())
                for f in reporte["filas"]
            ],
        )
        self.etiqueta_total.configure(text=f"Total confirmado: {formatear_moneda(reporte['total_confirmado'])}")

    # --- Ciclo de vida ---------------------------------------------------------------------------------

    @manejar_errores
    def refrescar(self) -> None:
        productos = self.controlador.productos()
        self._productos = {f"{p['codigo']} - {p['nombre']}": p["id"] for p in productos}
        self.combo_producto.configure(values=[TODOS] + list(self._productos))
        if self.var_producto.get() not in self._productos:
            self.var_producto.set(TODOS)
        self.cargar_inventario()
        self.cargar_movimientos()
        self.cargar_ventas()
        self.cargar_totales()
