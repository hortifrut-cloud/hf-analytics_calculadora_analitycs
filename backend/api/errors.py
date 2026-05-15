"""Excepciones de dominio y handlers de error para la API."""

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
