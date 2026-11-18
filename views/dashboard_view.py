"""Vista del panel principal (Inicio)."""
from __future__ import annotations

from tkinter import ttk

from utils.formatters import formatear_moneda
from views.widgets import (
    COLUMNAS_MOVIMIENTOS,
    FUENTE_CIFRA,
    FUENTE_SUBTITULO,
    PAD,
    crear_tabla,
    crear_titulo,
    fila_movimiento,
    llenar_tabla,
    manejar_errores,
)


class DashboardView(ttk.Frame):
    INDICADORES = (
        ("productos_activos", "Productos activos"),
        ("stock_bajo", "Stock bajo"),
        ("agotados", "Productos agotados"),
        ("ventas_hoy", "Ventas de hoy (COP)"),
    )

    def __init__(self, padre, controladores) -> None:
        super().__init__(padre, padding=PAD * 2)
        self.controlador = controladores.dashboard
        crear_titulo(self, "Inicio")

        tarjetas = ttk.Frame(self)
        tarjetas.pack(fill="x", pady=(0, PAD))
        self._cifras: dict[str, ttk.Label] = {}
        for columna, (clave, titulo) in enumerate(self.INDICADORES):
            marco = ttk.LabelFrame(tarjetas, text=titulo, padding=PAD)
            marco.grid(row=0, column=columna, padx=(0 if columna == 0 else PAD, 0), sticky="ew")
            tarjetas.columnconfigure(columna, weight=1, uniform="tarjeta")
            etiqueta = ttk.Label(marco, text="-", font=FUENTE_CIFRA)
            etiqueta.pack()
            self._cifras[clave] = etiqueta

        ttk.Label(self, text="Últimos movimientos de inventario", font=FUENTE_SUBTITULO).pack(
            anchor="w", pady=(PAD, 4)
        )
        marco_tabla, self.tabla = crear_tabla(self, COLUMNAS_MOVIMIENTOS, altura=14)
        marco_tabla.pack(fill="both", expand=True)

    @manejar_errores
    def refrescar(self) -> None:
        datos = self.controlador.resumen()
        self._cifras["productos_activos"].configure(text=str(datos["productos_activos"]))
        self._cifras["stock_bajo"].configure(text=str(datos["stock_bajo"]))
        self._cifras["agotados"].configure(text=str(datos["agotados"]))
        self._cifras["ventas_hoy"].configure(text=formatear_moneda(datos["ventas_hoy"]))
        llenar_tabla(self.tabla, [fila_movimiento(m) for m in datos["ultimos_movimientos"]])
