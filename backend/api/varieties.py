"""
Archivo: varieties.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Controlador para la gestión de variedades y sus parámetros técnicos. Permite
personalizar la configuración de cada variedad dentro de un escenario
específico, afectando directamente los cálculos productivos.

Acciones Principales:
    - Adición de nuevas variedades a un escenario existente.
    - Actualización masiva de parámetros (productividad, densidad, precios).
    - Gestión de la posición y ordenamiento de variedades.
    - Eliminación de variedades y limpieza de sus parámetros asociados.

Estructura Interna:
    - `create_variety`: Registra una nueva variedad con sus 7 años de parámetros.
    - `update_variety_params`: Sobrescribe la configuración técnica de una variedad.
    - `delete_variety`: Remueve la variedad del escenario.

Integración UI:
    - Este archivo renderiza la vista de configuración de variedades.
    - Es invocado por `routes.py` para procesar cambios técnicos.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.api.schemas import VarietyIn, VarietyParamsUpdateIn
from backend.db.models import Scenario, Variety, VarietyParam


def _get_session(request: Request):
    return request.app.state.SessionLocal()


async def create_variety(request: Request) -> JSONResponse:
    sid = int(request.path_params["id"])
    body = await request.json()
    data = VarietyIn.model_validate(body)

    with _get_session(request) as session:
        scenario = session.get(Scenario, sid)
        if scenario is None:
            return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)

        existing = session.query(Variety).filter_by(scenario_id=sid, name=data.name).first()
        if existing is not None:
            return JSONResponse(
                {"detail": f"Ya existe una variedad con nombre '{data.name}'."},
                status_code=409,
            )

        position = session.query(Variety).filter_by(scenario_id=sid).count()
        v_orm = Variety(scenario_id=sid, name=data.name, position=position)
        session.add(v_orm)
        session.flush()

        for p in data.params:
            session.add(
                VarietyParam(
                    variety_id=v_orm.id,
                    plant_year=p.plant_year,
                    productividad=p.productividad,
                    densidad=p.densidad,
                    precio_estimado=p.precio_estimado,
                    pct_recaudacion=p.pct_recaudacion,
                )
            )
        session.commit()
        vid = v_orm.id

    return JSONResponse({"id": vid, "name": data.name, "scenario_id": sid}, status_code=201)


async def update_variety_params(request: Request) -> JSONResponse:
    vid = int(request.path_params["id"])
    body = await request.json()
    data = VarietyParamsUpdateIn.model_validate(body)

    with _get_session(request) as session:
        v_orm = session.get(Variety, vid)
        if v_orm is None:
            return JSONResponse({"detail": "Variedad no encontrada."}, status_code=404)

        # Borrar params existentes y recrear
        for p in v_orm.params:
            session.delete(p)
        session.flush()

        for p in data.params:
            session.add(
                VarietyParam(
                    variety_id=vid,
                    plant_year=p.plant_year,
                    productividad=p.productividad,
                    densidad=p.densidad,
                    precio_estimado=p.precio_estimado,
                    pct_recaudacion=p.pct_recaudacion,
                )
            )
        session.commit()

    return JSONResponse({"id": vid, "updated": True})


async def delete_variety(request: Request) -> JSONResponse:
    vid = int(request.path_params["id"])

    with _get_session(request) as session:
        v_orm = session.get(Variety, vid)
        if v_orm is None:
            return JSONResponse({"detail": "Variedad no encontrada."}, status_code=404)
        session.delete(v_orm)
        session.commit()

    return JSONResponse({"deleted": True})
