"""Base común de los modelos: ejecución parametrizada y traducción de errores."""
from __future__ import annotations

import sqlite3
from typing import Any, Optional, Sequence

from utils.errors import ErrorDuplicado, ErrorNegocio, ErrorValidacion

_MENSAJES_UNICOS = {
    "productos.codigo": "Ya existe un producto con ese código.",
    "categorias.nombre": "Ya existe una categoría con ese nombre.",
    "detalle_venta.venta_id, detalle_venta.producto_id": (
        "El producto ya está registrado en esa venta."
    ),
}


def traducir_error_integridad(exc: sqlite3.IntegrityError) -> ErrorNegocio:
    """Convierte un error de integridad de SQLite en un error de negocio legible."""
    mensaje = str(exc)
    if mensaje.startswith("UNIQUE constraint failed:"):
        clave = mensaje.split(":", 1)[1].strip()
        return ErrorDuplicado(_MENSAJES_UNICOS.get(clave, "Ya existe un registro con esos datos."))
    if mensaje.startswith("FOREIGN KEY constraint failed"):
        return ErrorValidacion("El registro hace referencia a datos inexistentes o en uso.")
    if mensaje.startswith("CHECK constraint failed") or mensaje.startswith("NOT NULL constraint failed"):
        return ErrorValidacion(f"Los datos no cumplen las reglas de integridad ({mensaje}).")
    # Mensajes de los triggers (RAISE(ABORT, ...)) ya están redactados para el usuario.
    return ErrorValidacion(mensaje)


class BaseModel:
    """Acceso a datos mediante consultas parametrizadas (sin concatenar valores)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _ejecutar(self, sql: str, parametros: Sequence[Any] = ()) -> sqlite3.Cursor:
        try:
            return self.conn.execute(sql, tuple(parametros))
        except sqlite3.IntegrityError as exc:
            raise traducir_error_integridad(exc) from exc

    def _uno(self, sql: str, parametros: Sequence[Any] = ()) -> Optional[dict]:
        fila = self._ejecutar(sql, parametros).fetchone()
        return dict(fila) if fila is not None else None

    def _todos(self, sql: str, parametros: Sequence[Any] = ()) -> list[dict]:
        return [dict(fila) for fila in self._ejecutar(sql, parametros).fetchall()]


def filtro_fechas(columna: str, desde: Optional[str], hasta: Optional[str]) -> tuple[list[str], list[str]]:
    """Condiciones SQL para un rango de fechas 'AAAA-MM-DD' (ambos extremos inclusive).

    ``columna`` es siempre una constante interna del código, nunca entrada del usuario.
    """
    condiciones: list[str] = []
    parametros: list[str] = []
    if desde:
        condiciones.append(f"{columna} >= ?")
        parametros.append(desde)
    if hasta:
        condiciones.append(f"{columna} < date(?, '+1 day')")
        parametros.append(hasta)
    return condiciones, parametros
