"""Handler POST /api/scenarios/{id}/recompute."""

from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.db.repos import ScenarioRepo
from backend.logic.recompute import recompute


def _to_json(obj):
    """Convierte recursivamente numpy/pandas a tipos Python nativos para JSON."""
    import numpy as np

    if isinstance(obj, dict):
        return {str(k): _to_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json(v) for v in obj]
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _get_session(request: Request):
    return request.app.state.SessionLocal()


async def recompute_scenario(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        state = repo.get(sid)
    if state is None:
        return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)
    derived = recompute(state)
    # Excluir 'calculos' (tiene tuple keys, es interno); convertir numpy→python
    payload = {
        k: _to_json(v) for k, v in derived.items() if k != "calculos"
    }
    return JSONResponse(payload)
