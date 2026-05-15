"""
Archivo: state.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Puente reactivo para la gestión de estados entre la base de datos y la
interfaz Shiny. Implementa un caché en memoria por escenario para minimizar
round-trips a Supabase: las escrituras actualizan el caché en-place, por lo
que `trigger_reload()` retorna instantáneo sin re-leer la DB.

Acciones Principales:
    - Inyección de dependencia de sesión via `configure()`.
    - Lectura con caché en memoria: `load_scenario()` evita re-leer Supabase
      tras una escritura que ya actualizó el caché.
    - Escrituras que actualizan el caché in-place: `save_rules()`, `upsert_ha_cell()`,
      `batch_upsert_ha_cells()`.
    - Escrituras de variedades que invalidan el caché (requieren re-lectura por
      la complejidad de reconstruir params en memoria).

Estructura Interna:
    - `configure`: Registra la factoría de sesiones SQLAlchemy.
    - `load_scenario`: Carga el estado completo con caché en memoria.
    - `batch_upsert_ha_cells`: Persiste N celdas ha en una sola sesión de DB.
    - `save_rules`: Persiste reglas y actualiza caché sin re-leer DB.

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

# ---------------------------------------------------------------------------
# Caché en memoria por scenario_id
# ---------------------------------------------------------------------------
# ScenarioState es frozen (inmutable), por lo que model_copy() es seguro.
# Acceso thread-safe via GIL para operaciones simples de dict.
_state_cache: dict[int, ScenarioState] = {}


def _cache_get(scenario_id: int) -> ScenarioState | None:
    return _state_cache.get(scenario_id)


def _cache_set(scenario_id: int, state: ScenarioState) -> None:
    _state_cache[scenario_id] = state


def _cache_invalidate(scenario_id: int) -> None:
    _state_cache.pop(scenario_id, None)


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
    """
    Devuelve el ScenarioState desde caché en memoria si existe; si no, lo
    carga desde DB y lo almacena en caché para lecturas subsiguientes.

    Args:
        scenario_id (int): ID del escenario a cargar.

    Returns:
        ScenarioState | None: Estado del escenario o None si no existe.
    """
    cached = _cache_get(scenario_id)
    if cached is not None:
        return cached
    with _session() as s:
        result = ScenarioRepo(s).get(scenario_id)
    if result is not None:
        _cache_set(scenario_id, result)
    return result


def list_scenarios() -> list[tuple[int, str]]:
    with _session() as s:
        return ScenarioRepo(s).list_ids()


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------


def save_rules(scenario_id: int, rules: Rules) -> None:
    """
    Persiste las reglas en DB y actualiza el caché en memoria sin re-leer.

    Al actualizar solo el campo `rules` del ScenarioState en caché,
    `trigger_reload()` posterior retorna instantáneo (cache hit).

    Args:
        scenario_id (int): ID del escenario.
        rules (Rules): Nuevas reglas a persistir.
    """
    with _session() as s:
        RulesRepo(s).update(scenario_id, rules)
    # Actualizar caché en-place — evita un round-trip completo a Supabase
    cached = _cache_get(scenario_id)
    if cached is not None:
        _cache_set(scenario_id, cached.model_copy(update={"rules": rules}))


def batch_upsert_ha_cells(scenario_id: int, cells: list[NewProjectCell]) -> None:
    """
    Persiste múltiples celdas ha en una sola sesión de DB.

    Carga todos los mapas de referencia (seasons, varieties, groups, subrows,
    ha actuales) en batch al inicio, luego procesa todos los upserts sin
    queries adicionales. Reduce de N×8 queries a ~6 queries totales.

    Actualiza el caché en memoria al terminar para que `trigger_reload()`
    posterior sea un cache hit instantáneo.

    Args:
        scenario_id (int): ID del escenario.
        cells (list[NewProjectCell]): Celdas a persistir (solo las que cambiaron).
    """
    if not cells:
        return

    from backend.db.models import (
        NewProjectGroup,
        NewProjectHa,
        NewProjectSubrow,
        Season,
        Variety,
    )

    with _session() as s:
        # 1. Mapas de referencia en batch (una query cada uno)
        season_map: dict[str, int] = {
            row.code: row.id
            for row in s.query(Season).filter_by(scenario_id=scenario_id).all()
        }
        variety_map: dict[str, int] = {
            row.name: row.id
            for row in s.query(Variety).filter_by(scenario_id=scenario_id).all()
        }
        group_map: dict[str, int] = {
            row.kind: row.id
            for row in s.query(NewProjectGroup).filter_by(scenario_id=scenario_id).all()
        }

        # 2. Crear grupos faltantes
        for kind in {c.bloque.value for c in cells} - set(group_map):
            g = NewProjectGroup(scenario_id=scenario_id, kind=kind)
            s.add(g)
            s.flush()
            group_map[kind] = g.id

        # 3. Subrows de los grupos relevantes (una query con IN)
        relevant_gids = list({
            group_map[c.bloque.value] for c in cells if c.bloque.value in group_map
        })
        # (group_id, variety_id, label) → subrow_id
        subrow_map: dict[tuple[int, int, str], int] = {}
        if relevant_gids:
            for sr in s.query(NewProjectSubrow).filter(
                NewProjectSubrow.group_id.in_(relevant_gids)
            ).all():
                subrow_map[(sr.group_id, sr.variety_id, sr.label)] = sr.id

        # 4. Crear subrows faltantes
        for cell in cells:
            v_id = variety_map.get(cell.variety_name)
            g_id = group_map.get(cell.bloque.value)
            if v_id is None or g_id is None:
                continue
            key = (g_id, v_id, cell.sub_proyecto)
            if key not in subrow_map:
                sr = NewProjectSubrow(group_id=g_id, variety_id=v_id, label=cell.sub_proyecto)
                s.add(sr)
                s.flush()
                subrow_map[key] = sr.id

        # 5. Ha actuales de los subrows relevantes (una query con IN)
        relevant_sr_ids = list({
            subrow_map.get((
                group_map.get(c.bloque.value, -1),
                variety_map.get(c.variety_name, -1),
                c.sub_proyecto,
            ), -1)
            for c in cells
        } - {-1})
        ha_map: dict[tuple[int, int], NewProjectHa] = {}
        if relevant_sr_ids:
            for ha_obj in s.query(NewProjectHa).filter(
                NewProjectHa.subrow_id.in_(relevant_sr_ids)
            ).all():
                ha_map[(ha_obj.subrow_id, ha_obj.season_id)] = ha_obj

        # 6. Upsert de cada celda (sin queries adicionales)
        for cell in cells:
            g_id = group_map.get(cell.bloque.value)
            v_id = variety_map.get(cell.variety_name)
            s_id = season_map.get(cell.season)
            if g_id is None or v_id is None or s_id is None:
                continue
            sr_id = subrow_map.get((g_id, v_id, cell.sub_proyecto))
            if sr_id is None:
                continue
            ha_obj = ha_map.get((sr_id, s_id))
            if ha_obj is None:
                s.add(NewProjectHa(subrow_id=sr_id, season_id=s_id, hectareas=cell.hectareas))
            else:
                ha_obj.hectareas = cell.hectareas

        s.commit()

    # 7. Actualizar caché en memoria
    cached = _cache_get(scenario_id)
    if cached is not None:
        updated_map = {
            (c.bloque, c.sub_proyecto, c.variety_name, c.season): c.hectareas
            for c in cells
        }
        new_cells: list[NewProjectCell] = []
        for c in cached.new_project_cells:
            key = (c.bloque, c.sub_proyecto, c.variety_name, c.season)
            if key in updated_map:
                ha = updated_map.pop(key)
                if ha > 0:
                    new_cells.append(c.model_copy(update={"hectareas": ha}))
                # ha == 0 → no incluir (celda borrada)
            else:
                new_cells.append(c)
        # Celdas completamente nuevas (no existían antes en el caché)
        for (bloque, sub, vname, season), ha in updated_map.items():
            if ha > 0:
                new_cells.append(
                    NewProjectCell(
                        bloque=bloque,
                        sub_proyecto=sub,
                        variety_name=vname,
                        season=season,  # type: ignore[arg-type]
                        hectareas=ha,
                    )
                )
        _cache_set(scenario_id, cached.model_copy(update={"new_project_cells": new_cells}))


def upsert_ha_cell(scenario_id: int, cell: NewProjectCell) -> None:
    """Upsert de una celda de ha. Para múltiples celdas usar batch_upsert_ha_cells."""
    batch_upsert_ha_cells(scenario_id, [cell])


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
        result_id = v_orm.id
    # Invalidar caché — reconstruir varieties en memoria es complejo
    _cache_invalidate(scenario_id)
    return result_id


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

    scenario_id: int | None = None
    with _session() as s:
        v_orm = s.get(Variety, variety_id)
        if v_orm is None:
            return
        scenario_id = v_orm.scenario_id
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
    if scenario_id is not None:
        _cache_invalidate(scenario_id)


def delete_variety(variety_id: int) -> None:
    from backend.db.models import Variety

    scenario_id: int | None = None
    with _session() as s:
        v_orm = s.get(Variety, variety_id)
        if v_orm is None:
            return
        scenario_id = v_orm.scenario_id
        s.delete(v_orm)
        s.commit()
    if scenario_id is not None:
        _cache_invalidate(scenario_id)


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
