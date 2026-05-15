"""
Archivo: errors.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Gestor centralizado de excepciones y errores para la capa de API. Proporciona
handlers para traducir fallos de lógica de negocio o validación en respuestas
HTTP estandarizadas y amigables para el cliente.

Acciones Principales:
    - Manejo de excepciones de dominio (`DomainError`).
    - Validación de esquemas Pydantic con respuestas 422.
    - Control de errores de integridad referencial en base de datos.
    - Handler genérico para errores no controlados (500).

Estructura Interna:
    - `DomainError`: Excepción base para errores de negocio.
    - `*_error_handler`: Funciones de respuesta para diferentes tipos de fallo.

Ejemplo de Integración:
    from backend.api.errors import DomainError
    raise DomainError("El valor proporcionado no es válido")
"""

from starlette.requests import Request
from starlette.responses import JSONResponse


class DomainError(Exception):
    """Error de lógica de negocio → HTTP 400."""


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        return JSONResponse({"detail": exc.errors()}, status_code=422)
    return JSONResponse({"detail": str(exc)}, status_code=422)


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Conflicto de integridad en base de datos."}, status_code=409)


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "Error interno del servidor."}, status_code=500)
