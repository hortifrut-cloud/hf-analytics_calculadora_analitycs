from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from backend.api.errors import DomainError
from backend.api.routes import api_routes
from backend.shiny_app.app import app as shiny_app


async def status(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    # Solo inicializa si los tests no han inyectado ya SessionLocal
    _owned = not hasattr(app.state, "SessionLocal")
    if _owned:
        import backend.db.models as _m  # noqa: F401 — registra todos los modelos

        from backend.db.base import Base
        from backend.db.session import make_engine, make_session_factory
        from backend.settings import settings

        engine = make_engine(settings.database_url)
        Base.metadata.create_all(engine)
        app.state.engine = engine
        app.state.SessionLocal = make_session_factory(engine)

    # Inyectar session factory al bridge Shiny (siempre, incluyendo tests)
    from backend.shiny_app import state as shiny_state

    shiny_state.configure(app.state.SessionLocal)

    yield

    # Solo libera el engine si fue creado aquí (no en tests)
    if _owned and hasattr(app.state, "engine"):
        app.state.engine.dispose()


routes = [
    Route("/api/status", status),
    Mount("/api", routes=api_routes),
    Mount("/shiny", app=shiny_app),
    # StaticFiles SIEMPRE al final — ver plan_maestro.md §Fase 0
    Mount("/", app=StaticFiles(directory="backend/static", html=True), name="static"),
]

app = Starlette(
    routes=routes,
    lifespan=lifespan,
    exception_handlers={
        DomainError: lambda req, exc: JSONResponse({"detail": str(exc)}, status_code=400),
        ValidationError: lambda req, exc: JSONResponse(
            {"detail": exc.errors()}, status_code=422
        ),
        IntegrityError: lambda req, exc: JSONResponse(
            {"detail": "Conflicto de integridad en base de datos."}, status_code=409
        ),
        500: lambda req, exc: JSONResponse(
            {"detail": "Error interno del servidor."}, status_code=500
        ),
    },
)
