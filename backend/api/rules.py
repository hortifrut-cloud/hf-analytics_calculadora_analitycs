"""
Archivo: rules.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Controlador para la gestión de reglas de negocio técnico-económicas.
Permite la consulta y modificación de parámetros globales que rigen el
comportamiento financiero de los escenarios.

Acciones Principales:
    - Obtención de las reglas actuales de un escenario (royalties, costos).
    - Actualización de parámetros de financiamiento e intereses.

Estructura Interna:
    - `get_rules`: Recupera el objeto de reglas del repositorio.
    - `update_rules`: Aplica cambios en los parámetros globales de negocio.

Integración UI:
    - Este archivo renderiza la vista de reglas de negocio.
    - Es invocado por `routes.py` para la persistencia de parámetros globales.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.api.schemas import RulesIn
from backend.db.repos import RulesRepo
from backend.domain.inputs import Rules as PydanticRules


def _get_session(request: Request):
    return request.app.state.SessionLocal()


async def get_rules(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    with _get_session(request) as session:
        repo = RulesRepo(session)
        rules = repo.get(sid)
    if rules is None:
        return JSONResponse({"detail": "Reglas no encontradas."}, status_code=404)
    return JSONResponse(rules.model_dump())


async def update_rules(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    body = await request.json()
    data = RulesIn.model_validate(body)
    rules = PydanticRules(
        royaltie_fob=data.royaltie_fob,
        costo_plantines=data.costo_plantines,
        interes_financiamiento=data.interes_financiamiento,
        financiamiento_anios=data.financiamiento_anios,
    )
    with _get_session(request) as session:
        repo = RulesRepo(session)
        repo.update(sid, rules)
    return JSONResponse(rules.model_dump())
