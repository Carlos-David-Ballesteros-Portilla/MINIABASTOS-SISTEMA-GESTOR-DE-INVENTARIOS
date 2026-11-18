"""Vista de control de inventario: existencias/alertas, registro de movimientos e historial."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from controllers.inventario_controller import DIRECCION_NEGATIVO, DIRECCION_POSITIVO
from views.widgets import (
    COLUMNAS_MOVIMIENTOS,
    COLUMNAS_PRODUCTOS_STOCK,
    PAD,
    BarraFechas,
    crear_tabla,
    crear_titulo,
    fila_movimiento,
    fila_producto_stock,
    llenar_tabla,
    manejar_errores,
)

TIPOS_REGISTRO = (
    ("Entrada de mercancía", "ENTRADA"),
    ("Ajuste positivo", DIRECCION_POSITIVO),
    ("Ajuste negativo", DIRECCION_NEGATIVO),
)
TODOS = "Todos los productos"


def _etiqueta_producto(p: dict) -> str:
    return f"{p['codigo']} - {p['nombre']}"


class InventarioView(ttk.Frame):
    def __init__(self, padre, controladores) -> None:
        super().__init__(padre, padding=PAD * 2)
        self.controlador = controladores.inventario
        self._productos_activos: dict[str, int] = {}
        self._productos_todos: dict[str, int] = {}

        crear_titulo(self, "Inventario")
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True)
        self._construir_existencias(pestanas)
        self._construir_registro(pestanas)
        self._construir_historial(pestanas)

    # --- Pestaña 1: existencias y alertas -------------------------------------------------

    def _construir_existencias(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Existencias y alertas")
        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        ttk.Label(barra, text="Buscar:").pack(side="left")
        self.var_busqueda = tk.StringVar()
        entrada = ttk.Entry(barra, textvariable=self.var_busqueda, width=28)
        entrada.pack(side="left", padx=PAD)
        entrada.bind("<Return>", lambda _e: self.cargar_existencias())
        self.var_solo_alertas = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text="Solo alertas (agotados y stock bajo)", variable=self.var_solo_alertas,
            command=self.cargar_existencias,
        ).pack(side="left")
        ttk.Button(barra, text="Buscar", command=self.cargar_existencias).pack(side="left", padx=PAD)
        self.etiqueta_resumen = ttk.Label(marco, text="")
        self.etiqueta_resumen.pack(anchor="w", pady=(PAD, 4))
        tabla_marco, self.tabla_existencias = crear_tabla(marco, COLUMNAS_PRODUCTOS_STOCK, altura=16)
        tabla_marco.pack(fill="both", expand=True)

    @manejar_errores
    def cargar_existencias(self) -> None:
        filas = self.controlador.existencias(self.var_busqueda.get(), self.var_solo_alertas.get())
        llenar_tabla(self.tabla_existencias, [fila_producto_stock(p) for p in filas])
        agotados = sum(1 for p in filas if p["estado_stock"] == "AGOTADO")
        bajos = sum(1 for p in filas if p["estado_stock"] == "BAJO")
        self.etiqueta_resumen.configure(
            text=f"{len(filas)} productos mostrados  |  {agotados} agotados  |  {bajos} con stock bajo"
        )

    # --- Pestaña 2: registrar movimiento ---------------------------------------------------

    def _construir_registro(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD * 2)
        pestanas.add(marco, text="Registrar entrada o ajuste")
        self.var_producto = tk.StringVar()
        self.var_tipo = tk.StringVar(value=TIPOS_REGISTRO[0][0])
        self.var_cantidad = tk.StringVar()
        self.var_observacion = tk.StringVar()

        ttk.Label(marco, text="Producto *").grid(row=0, column=0, sticky="w", pady=6)
        self.combo_producto = ttk.Combobox(marco, textvariable=self.var_producto, state="readonly", width=48)
        self.combo_producto.grid(row=0, column=1, sticky="w", padx=PAD)
        ttk.Label(marco, text="Tipo de movimiento *").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            marco, textvariable=self.var_tipo, state="readonly", width=28,
            values=[t[0] for t in TIPOS_REGISTRO],
        ).grid(row=1, column=1, sticky="w", padx=PAD)
        ttk.Label(marco, text="Cantidad *").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(marco, textvariable=self.var_cantidad, width=16).grid(row=2, column=1, sticky="w", padx=PAD)
        ttk.Label(marco, text="Observación").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(marco, textvariable=self.var_observacion, width=60).grid(row=3, column=1, sticky="w", padx=PAD)
        ttk.Label(
            marco,
            text="La observación es obligatoria en los ajustes. La cantidad admite hasta 3 decimales (ej. 2, 0,5, 1,250).",
            foreground="#666666",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, PAD))
        ttk.Button(marco, text="Registrar movimiento", command=self.registrar).grid(
            row=5, column=1, sticky="w", padx=PAD, pady=PAD
        )

    @manejar_errores
    def registrar(self) -> None:
        producto_id = self._productos_activos.get(self.var_producto.get())
        tipo = dict(TIPOS_REGISTRO)[self.var_tipo.get()]
        if tipo == "ENTRADA":
            self.controlador.registrar_entrada(producto_id, self.var_cantidad.get(), self.var_observacion.get())
        else:
            self.controlador.registrar_ajuste(
                producto_id, tipo, self.var_cantidad.get(), self.var_observacion.get()
            )
        self.var_cantidad.set("")
        self.var_observacion.set("")
        self.cargar_existencias()
        messagebox.showinfo("Inventario", "Movimiento registrado correctamente.")

    # --- Pestaña 3: historial --------------------------------------------------------------

    def _construir_historial(self, pestanas) -> None:
        marco = ttk.Frame(pestanas, padding=PAD)
        pestanas.add(marco, text="Historial de movimientos")
        barra = ttk.Frame(marco)
        barra.pack(fill="x")
        self.var_filtro_producto = tk.StringVar(value=TODOS)
        ttk.Label(barra, text="Producto:").pack(side="left")
        self.combo_filtro = ttk.Combobox(barra, textvariable=self.var_filtro_producto, state="readonly", width=34)
        self.combo_filtro.pack(side="left", padx=PAD)
        self.fechas = BarraFechas(barra)
        self.fechas.pack(side="left")
        ttk.Button(barra, text="Consultar", command=self.cargar_historial).pack(side="left")
        tabla_marco, self.tabla_historial = crear_tabla(marco, COLUMNAS_MOVIMIENTOS, altura=16)
        tabla_marco.pack(fill="both", expand=True, pady=PAD)

    @manejar_errores
    def cargar_historial(self) -> None:
        desde, hasta = self.fechas.valores()
        producto_id = self._productos_todos.get(self.var_filtro_producto.get())
        movimientos = self.controlador.movimientos(producto_id, desde, hasta)
        llenar_tabla(self.tabla_historial, [fila_movimiento(m) for m in movimientos])

    # --- Ciclo de vida -----------------------------------------------------------------------

    @manejar_errores
    def refrescar(self) -> None:
        activos = self.controlador.productos(solo_activos=True)
        todos = self.controlador.productos(solo_activos=False)
        self._productos_activos = {_etiqueta_producto(p): p["id"] for p in activos}
        self._productos_todos = {_etiqueta_producto(p): p["id"] for p in todos}
        self.combo_producto.configure(values=list(self._productos_activos))
        if self.var_producto.get() not in self._productos_activos:
            self.var_producto.set("")
        self.combo_filtro.configure(values=[TODOS] + list(self._productos_todos))
        if self.var_filtro_producto.get() not in self._productos_todos:
            self.var_filtro_producto.set(TODOS)
        self.cargar_existencias()
        self.cargar_historial()
