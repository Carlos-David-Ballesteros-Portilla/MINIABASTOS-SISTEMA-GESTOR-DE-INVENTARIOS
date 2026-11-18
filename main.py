"""Punto de entrada de MINIABASTOS.

Uso:
    python main.py                 # base de datos real (miniabastos.db)
    python main.py --demo          # base de datos de demostración separada
    python main.py --db RUTA.db    # base de datos en otra ubicación
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from controllers.dashboard_controller import DashboardController
from controllers.inventario_controller import InventarioController
from controllers.producto_controller import ProductoController
from controllers.reporte_controller import ReporteController
from controllers.venta_controller import VentaController
from database.connection import RAIZ_PROYECTO, get_connection, ruta_bd_por_defecto
from database.initialization import inicializar_base_datos

RUTA_BD_DEMO = RAIZ_PROYECTO / "miniabastos_demo.db"


def _argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MINIABASTOS - Control de inventario")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--demo", action="store_true",
                       help="usa miniabastos_demo.db (separada de los datos reales) con datos de ejemplo")
    grupo.add_argument("--db", metavar="RUTA", help="ruta de la base de datos SQLite a usar")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _argumentos(argv)
    ruta = RUTA_BD_DEMO if args.demo else (Path(args.db) if args.db else ruta_bd_por_defecto())

    inicializar_base_datos(ruta)  # crea el archivo y el esquema si es la primera ejecución
    conn = get_connection(ruta)
    try:
        if args.demo:
            from demo_data import cargar_datos_demo

            cargar_datos_demo(conn)

        try:
            from views.main_view import VentanaPrincipal
        except ImportError as exc:  # tkinter no instalado
            print(f"No se pudo cargar la interfaz gráfica (Tkinter): {exc}", file=sys.stderr)
            print("En Linux instale el paquete 'python3-tk' e intente de nuevo.", file=sys.stderr)
            return 1

        controladores = SimpleNamespace(
            producto=ProductoController(conn),
            inventario=InventarioController(conn),
            venta=VentaController(conn),
            dashboard=DashboardController(conn),
            reporte=ReporteController(conn),
        )
        ventana = VentanaPrincipal(controladores)
        ventana.mainloop()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
