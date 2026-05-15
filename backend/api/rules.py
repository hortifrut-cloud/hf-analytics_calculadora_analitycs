"""Handlers GET/PUT para reglas de un escenario."""

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
