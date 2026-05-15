"""
Archivo: conftest.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Configuración de fixtures para pruebas de integración de la API. Provee un 
`TestClient` de Starlette configurado con una base de datos SQLite en 
memoria, garantizando que cada prueba se ejecute en un entorno limpio y 
aislado de la persistencia real.

Acciones Principales:
    - Inicialización de motores de base de datos efímeros (:memory:).
    - Creación de esquema de tablas bajo demanda para cada sesión de prueba.
    - Montaje de rutas de la API en una aplicación Starlette de prueba.
    - Inyección de factoría de sesiones en el estado de la aplicación.

Estructura Interna:
    - `api_client`: Fixture principal que entrega el cliente de pruebas.

Ejecución:
    Invocado automáticamente por pytest en el directorio tests/integration/.
"""

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.testclient import TestClient

import backend.db.models as _m  # noqa: F401 — registra todos los modelos ORM
from backend.api.routes import api_routes
from backend.db.base import Base
from backend.db.session import make_engine, make_session_factory


@pytest.fixture
def api_client():
    """TestClient con DB fresca en memoria para cada test."""
    eng = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)

    async def _status(req):
        return JSONResponse({"status": "ok"})

    test_app = Starlette(
        routes=[
            Route("/api/status", _status),
            Mount("/api", routes=api_routes),
        ]
    )
    test_app.state.SessionLocal = make_session_factory(eng)

    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c

    eng.dispose()
