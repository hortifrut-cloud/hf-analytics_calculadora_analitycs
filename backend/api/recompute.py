"""
Archivo: recompute.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Controlador para el disparo de recálculos masivos de un escenario.
Orquesta la ejecución de la lógica de negocio sobre el estado actual de la
base de datos y devuelve los resultados derivados listos para la UI.

Acciones Principales:
    - Recuperación del estado persistido del escenario.
    - Ejecución del motor de cálculo (`recompute`).
    - Serialización de resultados (incluyendo manejo de tipos NumPy).

Estructura Interna:
    - `recompute_scenario`: Handler que activa el motor de cálculo.
    - `_to_json`: Utilidad para la limpieza de tipos de datos complejos.

Integración UI:
    - Este archivo renderiza la vista de resultados financieros calculados.
    - Es invocado por `routes.py` tras cualquier modificación en los inputs.
"""

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
    payload = {k: _to_json(v) for k, v in derived.items() if k != "calculos"}
    return JSONResponse(payload)
