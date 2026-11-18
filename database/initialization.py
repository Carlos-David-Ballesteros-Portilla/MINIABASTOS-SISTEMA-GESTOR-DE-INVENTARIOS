"""Creación automática de la base de datos y su esquema."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from database.connection import get_connection, ruta_bd_por_defecto

RUTA_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def inicializar_base_datos(db_path: Optional[Union[str, Path]] = None) -> Path:
    """Crea el archivo de base de datos y el esquema si no existen.

    Es seguro llamarla en cada arranque: el esquema usa ``IF NOT EXISTS``.
    Devuelve la ruta de la base de datos.
    """
    ruta = Path(db_path) if db_path else ruta_bd_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(ruta)
    try:
        conn.executescript(RUTA_SCHEMA.read_text(encoding="utf-8"))
    finally:
        conn.close()
    return ruta
