"""Fixtures compartidos para tests de integración de la API."""

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
