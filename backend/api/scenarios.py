"""Handlers CRUD para escenarios."""

from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.api.errors import DomainError
from backend.api.schemas import ScenarioCreateIn
from backend.db.repos import ScenarioRepo
from backend.db.seeds import build_ui_png_scenario
from backend.domain.inputs import ScenarioState


def _get_session(request: Request):
    return request.app.state.SessionLocal()


async def list_scenarios(request: Request) -> JSONResponse:
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        items = repo.list_ids()
    return JSONResponse([{"id": i, "name": n} for i, n in items])


async def create_scenario(request: Request) -> JSONResponse:
    body = await request.json()
    data = ScenarioCreateIn.model_validate(body)
    seed = build_ui_png_scenario()
    # Crear escenario con nombre/país del request, resto de seed por defecto
    state = ScenarioState(
        name=data.name,
        base_table=seed.base_table,
        varieties=[],
        rules=seed.rules,
        new_project_cells=[],
    )
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        sid = repo.create(state)
    return JSONResponse({"id": sid, "name": data.name}, status_code=201)


async def get_scenario(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        state = repo.get(sid)
    if state is None:
        return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)
    return JSONResponse(state.model_dump())


async def delete_scenario(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        deleted = repo.delete(sid)
    if not deleted:
        return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)
    return JSONResponse({"deleted": True})
