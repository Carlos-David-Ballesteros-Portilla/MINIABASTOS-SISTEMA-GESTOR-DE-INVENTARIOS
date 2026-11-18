"""Conexión a SQLite y manejo de transacciones.

Las conexiones se abren en modo autocommit (``isolation_level=None``) y las
operaciones compuestas usan explícitamente :func:`transaccion`.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
NOMBRE_BD = "miniabastos.db"
VARIABLE_ENTORNO_BD = "MINIABASTOS_DB"


def ruta_bd_por_defecto() -> Path:
    """miniabastos.db en la raíz del proyecto (o la ruta de MINIABASTOS_DB)."""
    personalizada = os.environ.get(VARIABLE_ENTORNO_BD)
    return Path(personalizada) if personalizada else RAIZ_PROYECTO / NOMBRE_BD


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Abre una conexión con claves foráneas activadas y filas tipo diccionario."""
    ruta = Path(db_path) if db_path else ruta_bd_por_defecto()
    conn = sqlite3.connect(str(ruta), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:  # pragma: no cover
        conn.close()
        raise RuntimeError("No se pudieron activar las claves foráneas de SQLite.")
    return conn


@contextmanager
def transaccion(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Ejecuta un bloque en una única transacción: COMMIT al salir, ROLLBACK si falla.

    Si ya hay una transacción abierta (operaciones anidadas), el bloque se une
    a ella y es la transacción externa la que decide el COMMIT o ROLLBACK.
    """
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
