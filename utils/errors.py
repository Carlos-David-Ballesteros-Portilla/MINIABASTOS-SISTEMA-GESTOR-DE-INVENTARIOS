"""Excepciones de negocio de MINIABASTOS.

Todas heredan de ``ErrorNegocio``. Sus mensajes están pensados para mostrarse
tal cual al usuario final (en español).
"""
from __future__ import annotations


class ErrorNegocio(Exception):
    """Error base para cualquier regla de negocio o validación incumplida."""


class ErrorValidacion(ErrorNegocio):
    """Los datos recibidos no son válidos."""


class ErrorNoEncontrado(ErrorNegocio):
    """El registro solicitado no existe."""


class ErrorDuplicado(ErrorNegocio):
    """Se intentó crear un registro que ya existe (código o nombre repetido)."""


class ErrorStockInsuficiente(ErrorNegocio):
    """La operación dejaría las existencias en negativo."""


class ErrorEstadoInvalido(ErrorNegocio):
    """La operación no es válida para el estado actual del registro."""
