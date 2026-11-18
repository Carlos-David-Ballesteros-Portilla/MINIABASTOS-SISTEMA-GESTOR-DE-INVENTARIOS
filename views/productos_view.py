"""Vista de gestión de productos y categorías."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from utils.formatters import formatear_cantidad, formatear_moneda
from views.widgets import (
    CENTRO,
    DER,
    IZQ,
    PAD,
    crear_tabla,
    crear_titulo,
    id_seleccionado,
    llenar_tabla,
    manejar_errores,
)

UNIDADES_SUGERIDAS = ("unidad", "kg", "g", "libra", "litro", "ml", "paquete", "caja")

COLUMNAS = (
    ("codigo", "Código", 90, IZQ),
    ("nombre", "Nombre", 220, IZQ),
    ("categoria", "Categoría", 130, IZQ),
    ("unidad", "Unidad", 70, CENTRO),
    ("precio", "Precio", 90, DER),
    ("stock", "Existencias", 90, DER),
    ("minimo", "Stock mínimo", 90, DER),
    ("estado", "Estado", 80, CENTRO),
)


class ProductosView(ttk.Frame):
    def __init__(self, padre, controladores) -> None:
        super().__init__(padre, padding=PAD * 2)
        self.controlador = controladores.producto
        self._producto_id: Optional[int] = None
        self._productos: dict[int, dict] = {}
        self._categorias_por_nombre: dict[str, int] = {}

        crear_titulo(self, "Productos")

        # --- Búsqueda -----------------------------------------------------------
        barra = ttk.Frame(self)
        barra.pack(fill="x")
        ttk.Label(barra, text="Buscar (código o nombre):").pack(side="left")
        self.var_busqueda = tk.StringVar()
        entrada = ttk.Entry(barra, textvariable=self.var_busqueda, width=30)
        entrada.pack(side="left", padx=PAD)
        entrada.bind("<Return>", lambda _e: self.refrescar())
        self.var_inactivos = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            barra, text="Mostrar desactivados", variable=self.var_inactivos, command=self.refrescar
        ).pack(side="left")
        ttk.Button(barra, text="Buscar", command=self.refrescar).pack(side="left", padx=PAD)

        # --- Tabla ------------------------------------------------------------------
        marco, self.tabla = crear_tabla(self, COLUMNAS, altura=10)
        marco.pack(fill="both", expand=True, pady=PAD)
        self.tabla.bind("<<TreeviewSelect>>", lambda _e: self._cargar_seleccion())

        # --- Formulario ----------------------------------------------------------------
        formulario = ttk.LabelFrame(self, text="Datos del producto", padding=PAD)
        formulario.pack(fill="x")
        self.var_codigo = tk.StringVar()
        self.var_nombre = tk.StringVar()
        self.var_descripcion = tk.StringVar()
        self.var_unidad = tk.StringVar(value=UNIDADES_SUGERIDAS[0])
        self.var_categoria = tk.StringVar()
        self.var_precio = tk.StringVar()
        self.var_minimo = tk.StringVar()

        campos = (
            ("Código *", ttk.Entry(formulario, textvariable=self.var_codigo, width=18)),
            ("Nombre *", ttk.Entry(formulario, textvariable=self.var_nombre, width=34)),
            ("Descripción", ttk.Entry(formulario, textvariable=self.var_descripcion, width=34)),
            ("Unidad de medida *", ttk.Combobox(formulario, textvariable=self.var_unidad, values=UNIDADES_SUGERIDAS, width=16)),
        )
        self.combo_categoria = ttk.Combobox(formulario, textvariable=self.var_categoria, state="readonly", width=24)
        campos_derecha = (
            ("Categoría *", self.combo_categoria),
            ("Precio de venta (COP)", ttk.Entry(formulario, textvariable=self.var_precio, width=18)),
            ("Stock mínimo", ttk.Entry(formulario, textvariable=self.var_minimo, width=18)),
        )
        for fila, (texto, widget) in enumerate(campos):
            ttk.Label(formulario, text=texto).grid(row=fila, column=0, sticky="w", pady=3)
            widget.grid(row=fila, column=1, sticky="w", padx=(PAD, PAD * 3), pady=3)
        for fila, (texto, widget) in enumerate(campos_derecha):
            ttk.Label(formulario, text=texto).grid(row=fila, column=2, sticky="w", pady=3)
            widget.grid(row=fila, column=3, sticky="w", padx=(PAD, 0), pady=3)
        ttk.Label(
            formulario,
            text="Las existencias no se editan aquí: se modifican con entradas, ajustes y ventas en Inventario.",
            foreground="#666666",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        botones = ttk.Frame(self)
        botones.pack(fill="x", pady=(PAD, 0))
        ttk.Button(botones, text="Nuevo", command=self.nuevo).pack(side="left")
        ttk.Button(botones, text="Guardar", command=self.guardar).pack(side="left", padx=PAD)
        ttk.Button(botones, text="Desactivar", command=self.desactivar).pack(side="left")
        ttk.Button(botones, text="Reactivar", command=self.reactivar).pack(side="left", padx=PAD)
        ttk.Button(botones, text="Categorías...", command=self.abrir_categorias).pack(side="right")

    # --- Datos -------------------------------------------------------------------

    @manejar_errores
    def refrescar(self) -> None:
        self._recargar_categorias()
        filas = self.controlador.productos(
            self.var_busqueda.get(), solo_activos=not self.var_inactivos.get()
        )
        self._productos = {p["id"]: p for p in filas}
        llenar_tabla(self.tabla, [self._fila(p) for p in filas])

    @staticmethod
    def _fila(p: dict) -> tuple:
        valores = (
            p["codigo"], p["nombre"], p["categoria"], p["unidad_medida"],
            formatear_moneda(p["precio_venta"]),
            formatear_cantidad(p["stock_actual"]),
            formatear_cantidad(p["stock_minimo"]),
            "Activo" if p["activo"] else "Inactivo",
        )
        return p["id"], valores, () if p["activo"] else ("inactivo",)

    def _recargar_categorias(self) -> None:
        categorias = self.controlador.categorias()
        self._categorias_por_nombre = {c["nombre"]: c["id"] for c in categorias}
        self.combo_categoria.configure(values=list(self._categorias_por_nombre))

    # --- Formulario ------------------------------------------------------------------

    def nuevo(self) -> None:
        self._producto_id = None
        self.tabla.selection_remove(self.tabla.selection())
        for variable in (self.var_codigo, self.var_nombre, self.var_descripcion, self.var_categoria,
                         self.var_precio, self.var_minimo):
            variable.set("")
        self.var_unidad.set(UNIDADES_SUGERIDAS[0])

    def _cargar_seleccion(self) -> None:
        producto_id = id_seleccionado(self.tabla)
        producto = self._productos.get(producto_id)
        if producto is None:
            return
        self._producto_id = producto_id
        self.var_codigo.set(producto["codigo"])
        self.var_nombre.set(producto["nombre"])
        self.var_descripcion.set(producto["descripcion"] or "")
        self.var_unidad.set(producto["unidad_medida"])
        self.var_categoria.set(producto["categoria"])
        self.var_precio.set(str(producto["precio_venta"]))
        self.var_minimo.set(formatear_cantidad(producto["stock_minimo"]))

    @manejar_errores
    def guardar(self) -> None:
        datos = dict(
            codigo=self.var_codigo.get(),
            nombre=self.var_nombre.get(),
            descripcion=self.var_descripcion.get(),
            unidad=self.var_unidad.get(),
            categoria_id=self._categorias_por_nombre.get(self.var_categoria.get()),
            precio=self.var_precio.get(),
            stock_minimo=self.var_minimo.get(),
        )
        if self._producto_id is None:
            self.controlador.producto_crear(**datos)
            mensaje = "Producto registrado correctamente."
        else:
            self.controlador.producto_actualizar(self._producto_id, **datos)
            mensaje = "Producto actualizado correctamente."
        self.nuevo()
        self.refrescar()
        messagebox.showinfo("Productos", mensaje)

    @manejar_errores
    def desactivar(self) -> None:
        producto_id = id_seleccionado(self.tabla)
        if producto_id is None:
            messagebox.showinfo("Productos", "Seleccione un producto de la tabla.")
            return
        if messagebox.askyesno(
            "Desactivar producto",
            "El producto dejará de aparecer en nuevas ventas, pero conservará su historial.\n\n¿Desactivarlo?",
        ):
            self.controlador.producto_desactivar(producto_id)
            self.refrescar()

    @manejar_errores
    def reactivar(self) -> None:
        producto_id = id_seleccionado(self.tabla)
        if producto_id is None:
            messagebox.showinfo("Productos", "Seleccione un producto de la tabla.")
            return
        self.controlador.producto_reactivar(producto_id)
        self.refrescar()

    # --- Categorías -------------------------------------------------------------------------

    def abrir_categorias(self) -> None:
        DialogoCategorias(self, self.controlador, al_cambiar=self.refrescar)


class DialogoCategorias(tk.Toplevel):
    """Ventana para registrar, consultar y modificar categorías."""

    def __init__(self, padre, controlador, al_cambiar) -> None:
        super().__init__(padre)
        self.title("Categorías")
        self.transient(padre.winfo_toplevel())
        self.geometry("560x420")
        self.controlador = controlador
        self.al_cambiar = al_cambiar
        self._categoria_id: Optional[int] = None
        self._categorias: dict[int, dict] = {}

        contenido = ttk.Frame(self, padding=PAD * 2)
        contenido.pack(fill="both", expand=True)
        marco, self.tabla = crear_tabla(
            contenido, (("nombre", "Nombre", 180, IZQ), ("descripcion", "Descripción", 320, IZQ)), altura=8
        )
        marco.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", lambda _e: self._cargar_seleccion())

        formulario = ttk.Frame(contenido)
        formulario.pack(fill="x", pady=PAD)
        self.var_nombre = tk.StringVar()
        self.var_descripcion = tk.StringVar()
        ttk.Label(formulario, text="Nombre *").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(formulario, textvariable=self.var_nombre, width=30).grid(row=0, column=1, padx=PAD, pady=3)
        ttk.Label(formulario, text="Descripción").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(formulario, textvariable=self.var_descripcion, width=44).grid(row=1, column=1, padx=PAD, pady=3)

        botones = ttk.Frame(contenido)
        botones.pack(fill="x")
        ttk.Button(botones, text="Nueva", command=self.nueva).pack(side="left")
        ttk.Button(botones, text="Guardar", command=self.guardar).pack(side="left", padx=PAD)
        ttk.Button(botones, text="Cerrar", command=self.destroy).pack(side="right")
        self.recargar()

    @manejar_errores
    def recargar(self) -> None:
        categorias = self.controlador.categorias()
        self._categorias = {c["id"]: c for c in categorias}
        llenar_tabla(self.tabla, [(c["id"], (c["nombre"], c["descripcion"] or ""), ()) for c in categorias])

    def nueva(self) -> None:
        self._categoria_id = None
        self.tabla.selection_remove(self.tabla.selection())
        self.var_nombre.set("")
        self.var_descripcion.set("")

    def _cargar_seleccion(self) -> None:
        categoria = self._categorias.get(id_seleccionado(self.tabla))
        if categoria is None:
            return
        self._categoria_id = categoria["id"]
        self.var_nombre.set(categoria["nombre"])
        self.var_descripcion.set(categoria["descripcion"] or "")

    @manejar_errores
    def guardar(self) -> None:
        if self._categoria_id is None:
            self.controlador.categoria_crear(self.var_nombre.get(), self.var_descripcion.get())
        else:
            self.controlador.categoria_actualizar(
                self._categoria_id, self.var_nombre.get(), self.var_descripcion.get()
            )
        self.nueva()
        self.recargar()
        self.al_cambiar()
