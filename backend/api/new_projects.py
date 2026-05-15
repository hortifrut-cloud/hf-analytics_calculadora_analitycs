"""Handler upsert para celdas de hectáreas de Nuevos Proyectos."""

from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.api.schemas import NewProjectCellIn
from backend.db.models import NewProjectGroup, NewProjectHa, NewProjectSubrow, Scenario, Variety
from backend.db.repos import ScenarioRepo


def _get_session(request: Request):
    return request.app.state.SessionLocal()


async def upsert_cell(request: Request) -> JSONResponse:
    """PUT /api/scenarios/{id}/new-projects — upsert de una celda de ha."""
    sid = int(request.path_params["id"])
    body = await request.json()
    data = NewProjectCellIn.model_validate(body)

    with _get_session(request) as session:
        scenario = session.get(Scenario, sid)
        if scenario is None:
            return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)

        # Obtener season_id
        season_obj = next((s for s in scenario.seasons if s.code == data.season), None)
        if season_obj is None:
            return JSONResponse({"detail": f"Temporada '{data.season}' no encontrada."}, status_code=404)

        # Obtener variety_id
        variety = (
            session.query(Variety).filter_by(scenario_id=sid, name=data.variety_name).first()
        )
        if variety is None:
            return JSONResponse(
                {"detail": f"Variedad '{data.variety_name}' no encontrada en el escenario."},
                status_code=404,
            )

        bloque_val = data.bloque.value

        # Encontrar o crear group
        group = (
            session.query(NewProjectGroup)
            .filter_by(scenario_id=sid, kind=bloque_val)
            .first()
        )
        if group is None:
            group = NewProjectGroup(scenario_id=sid, kind=bloque_val)
            session.add(group)
            session.flush()

        # Encontrar o crear subrow (por group_id + variety_id + label)
        subrow = (
            session.query(NewProjectSubrow)
            .filter_by(group_id=group.id, variety_id=variety.id, label=data.sub_proyecto)
            .first()
        )
        if subrow is None:
            subrow = NewProjectSubrow(
                group_id=group.id, variety_id=variety.id, label=data.sub_proyecto
            )
            session.add(subrow)
            session.flush()

        # Upsert ha
        ha_obj = (
            session.query(NewProjectHa)
            .filter_by(subrow_id=subrow.id, season_id=season_obj.id)
            .first()
        )
        if ha_obj is None:
            ha_obj = NewProjectHa(
                subrow_id=subrow.id, season_id=season_obj.id, hectareas=data.hectareas
            )
            session.add(ha_obj)
        else:
            ha_obj.hectareas = data.hectareas

        session.commit()

    return JSONResponse(
        {
            "scenario_id": sid,
            "bloque": data.bloque.value,
            "sub_proyecto": data.sub_proyecto,
            "variety_name": data.variety_name,
            "season": data.season,
            "hectareas": data.hectareas,
        }
    )
