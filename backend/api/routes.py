"""Registro de rutas de la API."""

from starlette.routing import Route

from backend.api.exports import export_xlsx
from backend.api.new_projects import upsert_cell
from backend.api.recompute import recompute_scenario
from backend.api.rules import get_rules, update_rules
from backend.api.scenarios import (
    create_scenario,
    delete_scenario,
    get_scenario,
    list_scenarios,
)
from backend.api.varieties import create_variety, delete_variety, update_variety_params

_ALL_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


def _dispatch(methods_map: dict):
    """Despacha la request al handler correcto según método HTTP."""

    async def dispatch(request):
        handler = methods_map.get(request.method)
        if handler is None:
            from starlette.responses import JSONResponse

            return JSONResponse({"detail": "Método no permitido."}, status_code=405)
        return await handler(request)

    return dispatch


api_routes = [
    Route(
        "/scenarios",
        _dispatch({"GET": list_scenarios, "POST": create_scenario}),
        methods=["GET", "POST"],
    ),
    Route(
        "/scenarios/{id:int}",
        _dispatch({"GET": get_scenario, "DELETE": delete_scenario}),
        methods=["GET", "DELETE"],
    ),
    Route(
        "/scenarios/{id:int}/varieties",
        _dispatch({"POST": create_variety}),
        methods=["POST"],
    ),
    Route(
        "/varieties/{id:int}/params",
        _dispatch({"PUT": update_variety_params}),
        methods=["PUT"],
    ),
    Route(
        "/varieties/{id:int}",
        _dispatch({"DELETE": delete_variety}),
        methods=["DELETE"],
    ),
    Route(
        "/scenarios/{id:int}/rules",
        _dispatch({"GET": get_rules, "PUT": update_rules}),
        methods=["GET", "PUT"],
    ),
    Route(
        "/scenarios/{id:int}/new-projects",
        _dispatch({"PUT": upsert_cell}),
        methods=["PUT"],
    ),
    Route(
        "/scenarios/{id:int}/recompute",
        _dispatch({"POST": recompute_scenario}),
        methods=["POST"],
    ),
    Route(
        "/scenarios/{id:int}/export.xlsx",
        _dispatch({"GET": export_xlsx}),
        methods=["GET"],
    ),
]
