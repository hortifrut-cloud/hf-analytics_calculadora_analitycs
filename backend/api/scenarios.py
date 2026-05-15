"""
Archivo: scenarios.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Controlador de endpoints para la gestión de escenarios. Implementa las
operaciones CRUD básicas, permitiendo listar, obtener detalles, crear y
eliminar escenarios analíticos en el sistema.

Acciones Principales:
    - Listado de identificadores y nombres de escenarios disponibles.
    - Creación de nuevos escenarios basados en una plantilla canónica.
    - Recuperación del estado completo de un escenario para la UI.
    - Eliminación física de escenarios y sus datos relacionados.

Estructura Interna:
    - `list_scenarios`: Retorna la lista de escenarios existentes.
    - `create_scenario`: Inicializa un escenario con valores por defecto.
    - `get_scenario`: Devuelve el estado serializado del escenario.
    - `delete_scenario`: Elimina el recurso del sistema.

Integración UI:
    - Este archivo renderiza la vista de los escenarios.
    - Es invocado por `routes.py` mediante los handlers correspondientes.
"""

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
