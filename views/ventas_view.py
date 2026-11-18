"""Vista de ventas: registro de ventas con varios productos, historial, detalle y anulación."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from utils.formatters import formatear_cantidad, formatear_moneda
from views.widgets import (
    CENTRO,
    COLUMNAS_DETALLE_VENTA,
    COLUMNAS_VENTAS,
    DER,
    FUENTE_SUBTITULO,
    IZQ,
    PAD,
    BarraFechas,
    crear_tabla,
    crear_titulo,
    fila_detalle_venta,
    fila_venta,
    id_seleccionado,
    llenar_tabla,
    manejar_errores,
)

FILTROS_ESTADO = (("Todas", None), ("Confirmadas", "CONFIRMADA"), ("Anuladas", "ANULADA"))

COLUMNAS_BUSQUEDA = (
    ("codigo", "Código", 90, IZQ),
    ("nombre", "Producto", 250, IZQ),
    ("precio", "Precio", 90, DER),
    ("stock", "Disponible", 100, DER),
)
COLUMNAS_CARRITO = (
    ("codigo", "Código", 90, IZQ),
    ("nombre", "Producto", 250, IZQ),
    ("cantidad", "Cantidad", 90, DER),
    ("precio", "Precio unitario", 110, DER),
    ("subtotal", "Subtotal", 110, DER),
)


class VentasView(ttk.Frame):
    def __init__(self, padre, controladores) -> None:
        super().__init__(padre, padding=PAD * 2)
        self.controlador = controladores.venta
        self._resultados: dict[int, dict] = {}

        crear_titulo(self, "Ventas")
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True)
        self._construir_nueva_venta(pestanas)
        self._construir_historial(pestanas)

    # --- Pestaña 1: nueva venta -----------------------------------------------------------

    def _construir_nueva_venta(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Nueva venta")

        busqueda = ttk.Frame(marco)
        busqueda.pack(fill="x")
        ttk.Label(busqueda, text="Buscar producto (código o nombre):").pack(side="left")
        self.var_busqueda = tk.StringVar()
        entrada = ttk.Entry(busqueda, textvariable=self.var_busqueda, width=30)
        entrada.pack(side="left", padx=PAD)
        entrada.bind("<Return>", lambda _e: self.buscar())
        ttk.Button(busqueda, text="Buscar", command=self.buscar).pack(side="left")

        marco_resultados, self.tabla_busqueda = crear_tabla(marco, COLUMNAS_BUSQUEDA, altura=5)
        marco_resultados.pack(fill="x", pady=PAD)
        self.tabla_busqueda.bind("<<TreeviewSelect>>", lambda _e: self._producto_elegido())

        agregar = ttk.Frame(marco)
        agregar.pack(fill="x")
        self.var_cantidad = tk.StringVar(value="1")
        self.var_precio = tk.StringVar()
        ttk.Label(agregar, text="Cantidad:").pack(side="left")
        ttk.Entry(agregar, textvariable=self.var_cantidad, width=10).pack(side="left", padx=(4, PAD))
        ttk.Label(agregar, text="Precio unitario (COP):").pack(side="left")
        ttk.Entry(agregar, textvariable=self.var_precio, width=12).pack(side="left", padx=(4, PAD))
        ttk.Button(agregar, text="Agregar a la venta", command=self.agregar).pack(side="left")

        ttk.Label(marco, text="Productos de la venta", font=FUENTE_SUBTITULO).pack(anchor="w", pady=(PAD, 4))
        marco_carrito, self.tabla_carrito = crear_tabla(marco, COLUMNAS_CARRITO, altura=7)
        marco_carrito.pack(fill="both", expand=True)

        pie = ttk.Frame(marco)
        pie.pack(fill="x", pady=(PAD, 0))
        ttk.Button(pie, text="Quitar seleccionado", command=self.quitar).pack(side="left")
        ttk.Button(pie, text="Vaciar venta", command=self.vaciar).pack(side="left", padx=PAD)
        self.etiqueta_total = ttk.Label(pie, text="Total: $0", font=("Helvetica", 16, "bold"))
        self.etiqueta_total.pack(side="right")

        confirmacion = ttk.Frame(marco)
        confirmacion.pack(fill="x", pady=(PAD, 0))
        self.var_observaciones = tk.StringVar()
        ttk.Label(confirmacion, text="Observaciones:").pack(side="left")
        ttk.Entry(confirmacion, textvariable=self.var_observaciones, width=50).pack(side="left", padx=PAD)
        ttk.Button(confirmacion, text="Confirmar venta", command=self.confirmar).pack(side="right")

    @manejar_errores
    def buscar(self) -> None:
        productos = self.controlador.buscar_productos(self.var_busqueda.get())
        self._resultados = {p["id"]: p for p in productos}
        llenar_tabla(
            self.tabla_busqueda,
            [
                (p["id"], (p["codigo"], p["nombre"], formatear_moneda(p["precio_venta"]),
                           f"{formatear_cantidad(p['stock_actual'])} {p['unidad_medida']}"), ())
                for p in productos
            ],
        )

    def _producto_elegido(self) -> None:
        producto = self._resultados.get(id_seleccionado(self.tabla_busqueda))
        if producto is not None:
            self.var_precio.set(str(producto["precio_venta"]))

    @manejar_errores
    def agregar(self) -> None:
        producto_id = id_seleccionado(self.tabla_busqueda)
        carrito = self.controlador.agregar_al_carrito(producto_id, self.var_cantidad.get(), self.var_precio.get())
        self.var_cantidad.set("1")
        self._mostrar_carrito(carrito)

    @manejar_errores
    def quitar(self) -> None:
        producto_id = id_seleccionado(self.tabla_carrito)
        if producto_id is None:
            messagebox.showinfo("Ventas", "Seleccione una línea de la venta.")
            return
        self._mostrar_carrito(self.controlador.quitar_del_carrito(producto_id))

    @manejar_errores
    def vaciar(self) -> None:
        self.controlador.vaciar_carrito()
        self._mostrar_carrito(self.controlador.obtener_carrito())

    @manejar_errores
    def confirmar(self) -> None:
        venta = self.controlador.confirmar_venta(self.var_observaciones.get())
        self.var_observaciones.set("")
        self._mostrar_carrito(self.controlador.obtener_carrito())
        self.buscar()
        self.cargar_historial()
        messagebox.showinfo("Ventas", f"Venta #{venta['id']} registrada.\nTotal: {formatear_moneda(venta['total'])}")

    def _mostrar_carrito(self, carrito: dict) -> None:
        llenar_tabla(
            self.tabla_carrito,
            [
                (l["producto_id"],
                 (l["codigo"], l["nombre"], f"{formatear_cantidad(l['cantidad'])} {l['unidad_medida']}",
                  formatear_moneda(l["precio_unitario"]), formatear_moneda(l["subtotal"])), ())
                for l in carrito["lineas"]
            ],
        )
        self.etiqueta_total.configure(text=f"Total: {formatear_moneda(carrito['total'])}")

    # --- Pestaña 2: historial -------------------------------------------------------------------

    def _construir_historial(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Ventas anteriores")

        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        self.fechas = BarraFechas(barra)
        self.fechas.pack(side="left")
        self.var_estado = tk.StringVar(value=FILTROS_ESTADO[0][0])
        ttk.Label(barra, text="Estado:").pack(side="left")
        ttk.Combobox(
            barra, textvariable=self.var_estado, state="readonly", width=14,
            values=[f[0] for f in FILTROS_ESTADO],
        ).pack(side="left", padx=PAD)
        ttk.Button(barra, text="Consultar", command=self.cargar_historial).pack(side="left")

        marco_ventas, self.tabla_ventas = crear_tabla(marco, COLUMNAS_VENTAS, altura=8)
        marco_ventas.pack(fill="both", expand=True, pady=PAD)
        self.tabla_ventas.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalle())

        ttk.Label(marco, text="Detalle de la venta seleccionada", font=FUENTE_SUBTITULO).pack(anchor="w")
        marco_detalle, self.tabla_detalle = crear_tabla(marco, COLUMNAS_DETALLE_VENTA, altura=6)
        marco_detalle.pack(fill="both", expand=True, pady=(4, PAD))
        ttk.Button(marco, text="Anular venta seleccionada", command=self.anular).pack(anchor="e")

    @manejar_errores
    def cargar_historial(self) -> None:
        desde, hasta = self.fechas.valores()
        estado = dict(FILTROS_ESTADO)[self.var_estado.get()]
        ventas = self.controlador.ventas(desde, hasta, estado)
        llenar_tabla(self.tabla_ventas, [fila_venta(v) for v in ventas])
        llenar_tabla(self.tabla_detalle, [])

    @manejar_errores
    def _mostrar_detalle(self) -> None:
        venta_id: Optional[int] = id_seleccionado(self.tabla_ventas)
        if venta_id is None:
            return
        venta = self.controlador.detalle_venta(venta_id)
        llenar_tabla(self.tabla_detalle, [fila_detalle_venta(d) for d in venta["detalles"]])

    @manejar_errores
    def anular(self) -> None:
        venta_id = id_seleccionado(self.tabla_ventas)
        if venta_id is None:
            messagebox.showinfo("Ventas", "Seleccione una venta del historial.")
            return
        if not messagebox.askyesno(
            "Anular venta",
            f"Se anulará la venta #{venta_id} y se devolverán sus productos al inventario.\n"
            "Esta acción no se puede deshacer.\n\n¿Desea continuar?",
        ):
            return
        self.controlador.anular_venta(venta_id)
        self.cargar_historial()
        self.buscar()
        messagebox.showinfo("Ventas", f"La venta #{venta_id} fue anulada y el inventario restaurado.")

    # --- Ciclo de vida ----------------------------------------------------------------------------

    @manejar_errores
    def refrescar(self) -> None:
        self.buscar()
        self._mostrar_carrito(self.controlador.obtener_carrito())
        self.cargar_historial()
