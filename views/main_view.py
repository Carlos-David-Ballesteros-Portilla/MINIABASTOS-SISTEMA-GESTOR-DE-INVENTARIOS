"""Ventana principal: navegación lateral y área central de contenido."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from views.dashboard_view import DashboardView
from views.inventario_view import InventarioView
from views.productos_view import ProductosView
from views.reportes_view import ReportesView
from views.ventas_view import VentasView

COLOR_BARRA = "#1F3A4D"
COLOR_BOTON = "#1F3A4D"
COLOR_BOTON_ACTIVO = "#2F6F8F"
COLOR_TEXTO = "#FFFFFF"


class VentanaPrincipal(tk.Tk):
    SECCIONES = (
        ("Inicio", DashboardView),
        ("Productos", ProductosView),
        ("Inventario", InventarioView),
        ("Ventas", VentasView),
        ("Reportes", ReportesView),
    )

    def __init__(self, controladores) -> None:
        super().__init__()
        self.title("MINIABASTOS - Control de inventario")
        self.geometry("1200x760")
        self.minsize(1000, 640)
        ttk.Style(self).theme_use("clam" if "clam" in ttk.Style(self).theme_names() else "default")

        barra = tk.Frame(self, bg=COLOR_BARRA, width=190)
        barra.pack(side="left", fill="y")
        barra.pack_propagate(False)
        tk.Label(barra, text="MINIABASTOS", bg=COLOR_BARRA, fg=COLOR_TEXTO,
                 font=("Helvetica", 16, "bold")).pack(pady=(24, 2))
        tk.Label(barra, text="Control de inventario", bg=COLOR_BARRA, fg="#B8CCD9",
                 font=("Helvetica", 9)).pack(pady=(0, 24))

        contenido = ttk.Frame(self)
        contenido.pack(side="right", fill="both", expand=True)
        contenido.grid_rowconfigure(0, weight=1)
        contenido.grid_columnconfigure(0, weight=1)

        self._vistas: dict[str, ttk.Frame] = {}
        self._botones: dict[str, tk.Button] = {}
        for nombre, clase in self.SECCIONES:
            vista = clase(contenido, controladores)
            vista.grid(row=0, column=0, sticky="nsew")
            self._vistas[nombre] = vista
            boton = tk.Button(
                barra, text=nombre, command=lambda n=nombre: self.mostrar(n),
                bg=COLOR_BOTON, fg=COLOR_TEXTO, activebackground=COLOR_BOTON_ACTIVO,
                activeforeground=COLOR_TEXTO, relief="flat", bd=0, anchor="w",
                padx=20, pady=12, font=("Helvetica", 12), cursor="hand2",
            )
            boton.pack(fill="x")
            self._botones[nombre] = boton
        self.mostrar("Inicio")

    def mostrar(self, nombre: str) -> None:
        """Muestra la sección y recarga sus datos desde la base de datos."""
        for clave, boton in self._botones.items():
            boton.configure(bg=COLOR_BOTON_ACTIVO if clave == nombre else COLOR_BOTON)
        vista = self._vistas[nombre]
        vista.tkraise()
        vista.refrescar()
