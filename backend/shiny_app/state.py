"""
Archivo: state.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Puente reactivo para la gestión de estados entre la base de datos y la 
interfaz Shiny. Permite el acceso directo a `ScenarioState` sin necesidad 
de peticiones HTTP circulares, inyectando la factoría de sesiones de forma 
externa para mantener el desacoplamiento.

Acciones Principales:
    - Inyección de dependencia de sesión via `configure()`.
    - Lectura persistente de escenarios y listado de IDs.
    - Sincronización de reglas de negocio y celdas de proyectos.
    - Operaciones CRUD directas sobre variedades y sus parámetros técnicos.

Estructura Interna:
    - `configure`: Registra la factoría de sesiones SQLAlchemy.
    - `load_scenario`: Carga el estado completo de un escenario.
    - `upsert_ha_cell`: Sincroniza cambios en hectáreas con la DB.

Ejemplo de Integración:
    from backend.shiny_app import state
    state.configure(SessionLocal)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import sessionmaker

from backend.db.repos import RulesRepo, ScenarioRepo
from backend.domain.inputs import NewProjectCell, Rules, ScenarioState, VarietyParamRow

if TYPE_CHECKING:
    pass

_SessionLocal: sessionmaker | None = None  # type: ignore[type-arg]


def configure(session_factory: sessionmaker) -> None:  # type: ignore[type-arg]
    """Llamar desde el lifespan de app.py con la session factory activa."""
    global _SessionLocal
    _SessionLocal = session_factory


def _session():
    if _SessionLocal is None:
        raise RuntimeError(
            "shiny_app.state.configure() no fue llamado. "
            "Asegúrate de que el lifespan de app.py llame a configure()."
        )
    return _SessionLocal()


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------


def load_scenario(scenario_id: int) -> ScenarioState | None:
    with _session() as s:
        return ScenarioRepo(s).get(scenario_id)


def list_scenarios() -> list[tuple[int, str]]:
    with _session() as s:
        return ScenarioRepo(s).list_ids()


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------


def save_rules(scenario_id: int, rules: Rules) -> None:
    with _session() as s:
        RulesRepo(s).update(scenario_id, rules)


def upsert_ha_cell(scenario_id: int, cell: NewProjectCell) -> None:
    """Upsert de una celda de ha; replica la lógica del API handler."""
    from backend.db.models import (
        NewProjectGroup,
        NewProjectHa,
        NewProjectSubrow,
        Scenario,
        Variety,
    )

    with _session() as s:
        scenario = s.get(Scenario, scenario_id)
        if scenario is None:
            return

        season_obj = next((x for x in scenario.seasons if x.code == cell.season), None)
        if season_obj is None:
            return

        variety = (
            s.query(Variety)
            .filter_by(scenario_id=scenario_id, name=cell.variety_name)
            .first()
        )
        if variety is None:
            return

        bloque_val = cell.bloque.value
        group = (
            s.query(NewProjectGroup)
            .filter_by(scenario_id=scenario_id, kind=bloque_val)
            .first()
        )
        if group is None:
            group = NewProjectGroup(scenario_id=scenario_id, kind=bloque_val)
            s.add(group)
            s.flush()

        subrow = (
            s.query(NewProjectSubrow)
            .filter_by(group_id=group.id, variety_id=variety.id, label=cell.sub_proyecto)
            .first()
        )
        if subrow is None:
            subrow = NewProjectSubrow(
                group_id=group.id, variety_id=variety.id, label=cell.sub_proyecto
            )
            s.add(subrow)
            s.flush()

        ha_obj = (
            s.query(NewProjectHa)
            .filter_by(subrow_id=subrow.id, season_id=season_obj.id)
            .first()
        )
        if ha_obj is None:
            s.add(
                NewProjectHa(
                    subrow_id=subrow.id,
                    season_id=season_obj.id,
                    hectareas=cell.hectareas,
                )
            )
        else:
            ha_obj.hectareas = cell.hectareas

        s.commit()


def create_variety(
    scenario_id: int, name: str, params: list[VarietyParamRow]
) -> int | None:
    """Crea una variedad nueva. Devuelve el ID o None si el nombre ya existe."""
    from backend.db.models import Scenario, Variety, VarietyParam

    with _session() as s:
        scenario = s.get(Scenario, scenario_id)
        if scenario is None:
            return None
        existing = s.query(Variety).filter_by(scenario_id=scenario_id, name=name).first()
        if existing is not None:
            return None
        position = s.query(Variety).filter_by(scenario_id=scenario_id).count()
        v_orm = Variety(scenario_id=scenario_id, name=name, position=position)
        s.add(v_orm)
        s.flush()
        for p in params:
            s.add(
                VarietyParam(
                    variety_id=v_orm.id,
                    plant_year=p.plant_year,
                    productividad=p.productividad,
                    densidad=p.densidad,
                    precio_estimado=p.precio_estimado,
                    pct_recaudacion=p.pct_recaudacion,
                )
            )
        s.commit()
        return v_orm.id


def update_variety_params(variety_id: int, params: list[VarietyParamRow]) -> None:
    """
    Actualiza los parámetros de una variedad con un bulk delete + bulk insert.

    Reemplaza el loop individual de DELETE por un único DELETE WHERE y usa
    `bulk_insert_mappings` para insertar los 7 años en una sola operación,
    reduciendo de ~14 queries a 2 queries en total.

    Args:
        variety_id (int): ID de la variedad a actualizar.
        params (list[VarietyParamRow]): Lista de 7 filas de parámetros.
    """
    from backend.db.models import Variety, VarietyParam

    with _session() as s:
        v_orm = s.get(Variety, variety_id)
        if v_orm is None:
            return
        # Un solo DELETE WHERE en vez de N DELETEs individuales por fila
        s.execute(sql_delete(VarietyParam).where(VarietyParam.variety_id == variety_id))
        s.flush()
        # Bulk insert: 7 filas en una sola operación
        s.bulk_insert_mappings(
            VarietyParam,
            [
                {
                    "variety_id": variety_id,
                    "plant_year": p.plant_year,
                    "productividad": p.productividad,
                    "densidad": p.densidad,
                    "precio_estimado": p.precio_estimado,
                    "pct_recaudacion": p.pct_recaudacion,
                }
                for p in params
            ],
        )
        s.commit()


def delete_variety(variety_id: int) -> None:
    from backend.db.models import Variety

    with _session() as s:
        v_orm = s.get(Variety, variety_id)
        if v_orm is None:
            return
        s.delete(v_orm)
        s.commit()


def get_variety_id(scenario_id: int, variety_name: str) -> int | None:
    from backend.db.models import Variety

    with _session() as s:
        v = s.query(Variety).filter_by(scenario_id=scenario_id, name=variety_name).first()
        return v.id if v else None


def variety_has_ha(scenario_id: int, variety_name: str) -> bool:
    """Devuelve True si hay celdas de ha asignadas a esta variedad."""
    from backend.db.models import NewProjectHa, NewProjectSubrow, Variety

    with _session() as s:
        v = s.query(Variety).filter_by(scenario_id=scenario_id, name=variety_name).first()
        if v is None:
            return False
        has_ha = (
            s.query(NewProjectHa)
            .join(NewProjectSubrow, NewProjectHa.subrow_id == NewProjectSubrow.id)
            .filter(NewProjectSubrow.variety_id == v.id, NewProjectHa.hectareas > 0)
            .first()
        )
        return has_ha is not None
