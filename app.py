from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from backend.shiny_app.app import app as shiny_app


async def status(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


routes = [
    Route("/api/status", status),
    Mount("/shiny", app=shiny_app),
    # StaticFiles ALWAYS last — see docs/plan/plan_maestro.md §Fase 0
    Mount("/", app=StaticFiles(directory="backend/static", html=True), name="static"),
]

app = Starlette(routes=routes)
