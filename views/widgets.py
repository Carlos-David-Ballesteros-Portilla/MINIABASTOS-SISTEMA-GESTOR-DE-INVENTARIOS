"""Componentes de interfaz reutilizables (solo presentación, sin SQL ni reglas de negocio)."""
from __future__ import annotations

import logging
import tkinter as tk
from functools import wraps
from tkinter import messagebox, ttk
from typing import Iterable, Optional, Sequence

from utils.errors import ErrorNegocio
from utils.formatters import (
    formatear_cantidad,
    formatear_estado_stock,
    formatear_moneda,
    formatear_tipo_movimiento,
)

PAD = 10
FUENTE_TITULO = ("Helvetica", 18, "bold")
FUENTE_SUBTITULO = ("Helvetica", 12, "bold")
FUENTE_CIFRA = ("Helvetica", 22, "bold")

IZQ, CENTRO, DER = "w", "center", "e"

# Columnas comunes para tablas de movimientos: (id, título, ancho, alineación)
COLUMNAS_MOVIMIENTOS = (
    ("fecha", "Fecha", 140, IZQ),
    ("producto", "Producto", 230, IZQ),
    ("tipo", "Tipo", 90, IZQ),
    ("cantidad", "Cantidad", 80, DER),
    ("anterior", "Stock anterior", 100, DER),
    ("posterior", "Stock posterior", 100, DER),
    ("venta", "Venta", 60, CENTRO),
    ("observacion", "Observación", 240, IZQ),
)

COLUMNAS_PRODUCTOS_STOCK = (
    ("codigo", "Código", 90, IZQ),
    ("nombre", "Producto", 240, IZQ),
    ("categoria", "Categoría", 130, IZQ),
    ("unidad", "Unidad", 70, CENTRO),
    ("stock", "Existencias", 90, DER),
    ("minimo", "Stock mínimo", 90, DER),
    ("estado", "Estado", 100, CENTRO),
)

COLUMNAS_VENTAS = (
    ("id", "N.º", 60, CENTRO),
    ("fecha", "Fecha", 150, IZQ),
    ("total", "Total", 110, DER),
    ("estado", "Estado", 100, CENTRO),
    ("observaciones", "Observaciones", 300, IZQ),
)

COLUMNAS_DETALLE_VENTA = (
    ("codigo", "Código", 90, IZQ),
    ("producto", "Producto", 260, IZQ),
    ("cantidad", "Cantidad", 90, DER),
    ("precio", "Precio unitario", 110, DER),
    ("subtotal", "Subtotal", 110, DER),
)


def manejar_errores(metodo):
    """Muestra al usuario los errores de negocio (y cualquier error inesperado) en un diálogo."""

    @wraps(metodo)
    def envoltura(self, *args, **kwargs):
        try:
            return metodo(self, *args, **kwargs)
        except ErrorNegocio as exc:
            messagebox.showwarning("No se pudo completar la acción", str(exc))
        except Exception:
            logging.exception("Error inesperado en la interfaz")
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un error inesperado. Intente de nuevo; si persiste, revise el registro de la aplicación.",
            )
        return None

    return envoltura


def crear_titulo(padre, texto: str) -> ttk.Label:
    etiqueta = ttk.Label(padre, text=texto, font=FUENTE_TITULO)
    etiqueta.pack(anchor="w", pady=(0, PAD))
    return etiqueta


def crear_tabla(padre, columnas: Sequence[tuple], altura: int = 10) -> tuple[ttk.Frame, ttk.Treeview]:
    """Treeview con barra de desplazamiento. Devuelve (marco, tabla)."""
    marco = ttk.Frame(padre)
    tabla = ttk.Treeview(
        marco, columns=[c[0] for c in columnas], show="headings", height=altura, selectmode="browse"
    )
    for id_columna, titulo, ancho, ancla in columnas:
        tabla.heading(id_columna, text=titulo)
        tabla.column(id_columna, width=ancho, anchor=ancla, stretch=True)
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    tabla.tag_configure("anulada", foreground="#888888")
    tabla.tag_configure("agotado", foreground="#B00020")
    tabla.tag_configure("bajo", foreground="#B26A00")
    tabla.tag_configure("inactivo", foreground="#888888")
    return marco, tabla


def llenar_tabla(tabla: ttk.Treeview, filas: Iterable[tuple]) -> None:
    """``filas``: iterable de (iid | None, valores, etiquetas)."""
    tabla.delete(*tabla.get_children())
    for iid, valores, etiquetas in filas:
        opciones = {"values": valores, "tags": etiquetas}
        if iid is not None:
            opciones["iid"] = str(iid)
        tabla.insert("", "end", **opciones)


def id_seleccionado(tabla: ttk.Treeview) -> Optional[int]:
    seleccion = tabla.selection()
    return int(seleccion[0]) if seleccion else None


def etiqueta_estado_stock(producto: dict) -> tuple[str, tuple]:
    estado = producto["estado_stock"]
    etiquetas = {"AGOTADO": ("agotado",), "BAJO": ("bajo",)}.get(estado, ())
    return formatear_estado_stock(estado), etiquetas


def fila_producto_stock(producto: dict) -> tuple:
    estado, etiquetas = etiqueta_estado_stock(producto)
    valores = (
        producto["codigo"],
        producto["nombre"],
        producto["categoria"],
        producto["unidad_medida"],
        formatear_cantidad(producto["stock_actual"]),
        formatear_cantidad(producto["stock_minimo"]),
        estado,
    )
    return producto["id"], valores, etiquetas


def fila_movimiento(mov: dict) -> tuple:
    valores = (
        mov["fecha"],
        f"{mov['codigo']} - {mov['producto']}",
        formatear_tipo_movimiento(mov["tipo"]),
        formatear_cantidad(mov["cantidad"]),
        formatear_cantidad(mov["stock_anterior"]),
        formatear_cantidad(mov["stock_posterior"]),
        f"#{mov['venta_id']}" if mov.get("venta_id") else "",
        mov["observacion"] or "",
    )
    return None, valores, ()


def fila_venta(venta: dict) -> tuple:
    anulada = venta["estado"] == "ANULADA"
    valores = (
        venta["id"],
        venta["fecha"],
        formatear_moneda(venta["total"]),
        "Anulada" if anulada else "Confirmada",
        venta["observaciones"] or "",
    )
    return venta["id"], valores, ("anulada",) if anulada else ()


def fila_detalle_venta(detalle: dict) -> tuple:
    valores = (
        detalle["codigo"],
        detalle["producto"],
        f"{formatear_cantidad(detalle['cantidad'])} {detalle['unidad_medida']}",
        formatear_moneda(detalle["precio_unitario"]),
        formatear_moneda(detalle["subtotal"]),
    )
    return detalle["id"], valores, ()


class BarraFechas(ttk.Frame):
    """Par de campos 'Desde' / 'Hasta' (AAAA-MM-DD). La validación la hace el controlador."""

    def __init__(self, padre) -> None:
        super().__init__(padre)
        self.var_desde = tk.StringVar()
        self.var_hasta = tk.StringVar()
        ttk.Label(self, text="Desde (AAAA-MM-DD):").pack(side="left")
        ttk.Entry(self, textvariable=self.var_desde, width=12).pack(side="left", padx=(4, PAD))
        ttk.Label(self, text="Hasta (AAAA-MM-DD):").pack(side="left")
        ttk.Entry(self, textvariable=self.var_hasta, width=12).pack(side="left", padx=(4, PAD))

    def valores(self) -> tuple[str, str]:
        return self.var_desde.get(), self.var_hasta.get()

    def limpiar(self) -> None:
        self.var_desde.set("")
        self.var_hasta.set("")
