"""Acceso a datos de categorías."""
from __future__ import annotations

from typing import Optional

from models.base_model import BaseModel


class CategoriaModel(BaseModel):
    def crear(self, nombre: str, descripcion: Optional[str] = None) -> int:
        cursor = self._ejecutar(
            "INSERT INTO categorias (nombre, descripcion) VALUES (?, ?)",
            (nombre, descripcion),
        )
        return cursor.lastrowid

    def actualizar(self, categoria_id: int, nombre: str, descripcion: Optional[str] = None) -> bool:
        cursor = self._ejecutar(
            "UPDATE categorias SET nombre = ?, descripcion = ? WHERE id = ?",
            (nombre, descripcion, categoria_id),
        )
        return cursor.rowcount > 0

    def obtener(self, categoria_id: int) -> Optional[dict]:
        return self._uno(
            "SELECT id, nombre, descripcion FROM categorias WHERE id = ?", (categoria_id,)
        )

    def listar(self) -> list[dict]:
        return self._todos("SELECT id, nombre, descripcion FROM categorias ORDER BY nombre")
