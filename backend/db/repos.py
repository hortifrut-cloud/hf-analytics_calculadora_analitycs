"""
Archivo: repos.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Capa de Repositorios para el acceso y persistencia de datos. Actúa como 
mediador entre los modelos ORM de SQLAlchemy y los modelos Pydantic del 
dominio, centralizando la lógica de consulta y comando.

Acciones Principales:
    - Persistencia de estados de escenario completos (ScenarioState).
    - CRUD de reglas de negocio y parámetros de variedades.
    - Registro de auditoría mediante la capa de servicios.
    - Conversión bidireccional entre objetos de base de datos y objetos de negocio.

Estructura Interna:
    - `ScenarioRepo`: Gestiona el ciclo de vida de los escenarios.
    - `RulesRepo`: Gestiona las reglas técnico-económicas.
    - `AuditRepo`: Gestiona el rastro de auditoría.

Ejemplo de Integración:
    from backend.db.repos import ScenarioRepo
    repo = ScenarioRepo(session)
    scenario = repo.get(scenario_id)
"""

from typing import Any, cast

from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session, selectinload

from backend.db.models import (
    AuditLog,
    BaseTableRow,
    BaseTableValue,
    BaseTableVariation,
    NewProjectGroup,
    NewProjectHa,
    NewProjectSubrow,
    Rules,
    Scenario,
    Season,
    Variety,
    VarietyParam,
)
from backend.domain.enums import ALL_SEASONS, BloqueKind, SeasonCode
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow as PydanticBTRow,
    NewProjectCell,
    Rules as PydanticRules,
    ScenarioState,
    Variety as PydanticVariety,
    VarietyParamRow,
)

_SEASONS = ALL_SEASONS


# ---------------------------------------------------------------------------
# Helpers de conversión ORM → Pydantic
# ---------------------------------------------------------------------------


def _season_map(session: Session, scenario_id: int) -> dict[str, int]:
    """Devuelve {code: season_id}."""
    seasons = session.query(Season).filter_by(scenario_id=scenario_id).all()
    return {s.code: s.id for s in seasons}


def _orm_to_pydantic_scenario(
    orm: Scenario,
    session: Session,
) -> ScenarioState:
    season_map = {s.id: s.code for s in orm.seasons}

    # BaseTable rows
    pydantic_rows = []
    for row in orm.base_table_rows:
        values = {season_map[v.season_id]: v.value for v in row.values}
        pydantic_rows.append(
            PydanticBTRow(
                project_name=row.project_name,
                unit=row.unit,
                values={s: values.get(s, 0.0) for s in _SEASONS},
                total=row.total,
            )
        )
    variation = {season_map[v.season_id]: v.value for v in orm.base_table_variation}
    base_table = BaseTable(
        rows=pydantic_rows,
        variation={s: variation.get(s, 0.0) for s in _SEASONS},
    )

    # Varieties
    pydantic_varieties = []
    for v in orm.varieties:
        params = sorted(v.params, key=lambda p: p.plant_year)
        pydantic_varieties.append(
            PydanticVariety(
                name=v.name,
                params=[
                    VarietyParamRow(
                        plant_year=p.plant_year,
                        productividad=p.productividad,
                        densidad=p.densidad,
                        precio_estimado=p.precio_estimado,
                        pct_recaudacion=p.pct_recaudacion,
                    )
                    for p in params
                ],
            )
        )

    # Rules
    r = orm.rules
    pydantic_rules = PydanticRules(
        royaltie_fob=r.royaltie_fob if r else 0.12,
        costo_plantines=r.costo_plantines if r else 3.5,
        interes_financiamiento=r.interes_financiamiento if r else 0.0,
        financiamiento_anios=r.financiamiento_anios if r else 5,
    )

    # NewProjectCells + subproyectos activos (labels distintos por (bloque, variedad))
    cells: list[NewProjectCell] = []
    variety_id_to_name = {v.id: v.name for v in orm.varieties}
    subproyectos: dict[str, dict[str, list[str]]] = {}
    for group in orm.new_project_groups:
        bloque = BloqueKind(group.kind)
        by_variety: dict[str, list[str]] = {}
        seen: dict[str, set[str]] = {}
        for subrow in group.subrows:
            variety_name = variety_id_to_name.get(subrow.variety_id, "")
            if not variety_name:
                continue
            if variety_name not in seen:
                by_variety[variety_name] = []
                seen[variety_name] = set()
            if subrow.label not in seen[variety_name]:
                by_variety[variety_name].append(subrow.label)
                seen[variety_name].add(subrow.label)
            for ha in subrow.ha_values:
                if ha.hectareas > 0:
                    cells.append(
                        NewProjectCell(
                            bloque=bloque,
                            sub_proyecto=subrow.label,
                            variety_name=variety_name,
                            season=season_map[ha.season_id],
                            hectareas=ha.hectareas,
                        )
                    )
        if by_variety:
            subproyectos[group.kind] = by_variety

    return ScenarioState(
        name=orm.name,
        base_table=base_table,
        varieties=pydantic_varieties,
        rules=pydantic_rules,
        new_project_cells=cells,
        subproyectos=subproyectos,
    )


# ---------------------------------------------------------------------------
# ScenarioRepo
# ---------------------------------------------------------------------------


class ScenarioRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, state: ScenarioState) -> int:
        """Persiste un ScenarioState completo. Devuelve el ID generado."""
        orm = Scenario(name=state.name)
        self.session.add(orm)
        self.session.flush()  # obtiene orm.id

        # Seasons
        season_objs = []
        for i, code in enumerate(_SEASONS):
            s = Season(scenario_id=orm.id, code=code, ordinal=i)
            self.session.add(s)
            season_objs.append(s)
        self.session.flush()
        season_map = {s.code: s.id for s in season_objs}

        # BaseTable rows
        for row in state.base_table.rows:
            bt_row = BaseTableRow(
                scenario_id=orm.id,
                project_name=row.project_name,
                unit=row.unit,
                total=row.total,
            )
            self.session.add(bt_row)
            self.session.flush()
            for code_raw, val in row.values.items():
                code = cast(SeasonCode, code_raw)
                self.session.add(
                    BaseTableValue(
                        base_table_row_id=bt_row.id,
                        season_id=season_map[code],
                        value=val,
                    )
                )

        # Variation
        for code_raw, val in state.base_table.variation.items():
            code = cast(SeasonCode, code_raw)
            self.session.add(
                BaseTableVariation(
                    scenario_id=orm.id,
                    season_id=season_map[code],
                    value=val,
                )
            )

        # Rules
        r = state.rules
        self.session.add(
            Rules(
                scenario_id=orm.id,
                royaltie_fob=r.royaltie_fob,
                costo_plantines=r.costo_plantines,
                interes_financiamiento=r.interes_financiamiento,
                financiamiento_anios=r.financiamiento_anios,
            )
        )

        # Varieties
        variety_name_to_id: dict[str, int] = {}
        for pos, variety in enumerate(state.varieties):
            v_orm = Variety(scenario_id=orm.id, name=variety.name, position=pos)
            self.session.add(v_orm)
            self.session.flush()
            variety_name_to_id[variety.name] = v_orm.id
            for p in variety.params:
                self.session.add(
                    VarietyParam(
                        variety_id=v_orm.id,
                        plant_year=p.plant_year,
                        productividad=p.productividad,
                        densidad=p.densidad,
                        precio_estimado=p.precio_estimado,
                        pct_recaudacion=p.pct_recaudacion,
                    )
                )

        # NewProjectCells → groups/subrows/ha
        # Agrupa celdas por (bloque, sub_proyecto, variety_name)
        from collections import defaultdict

        groups: dict[tuple[str, str, str], list[NewProjectCell]] = defaultdict(list)
        for cell in state.new_project_cells:
            groups[(cell.bloque.value, cell.sub_proyecto, cell.variety_name)].append(cell)

        group_key_to_orm: dict[tuple[str, str], int] = {}  # (bloque, sub_proyecto) → group_id
        for (bloque_val, sub_proyecto, variety_name), cells in groups.items():
            gkey = (bloque_val, sub_proyecto)
            if gkey not in group_key_to_orm:
                g = NewProjectGroup(scenario_id=orm.id, kind=bloque_val)
                self.session.add(g)
                self.session.flush()
                group_key_to_orm[gkey] = g.id

            g_id = group_key_to_orm[gkey]
            v_id = variety_name_to_id[variety_name]
            subrow = NewProjectSubrow(group_id=g_id, variety_id=v_id, label=sub_proyecto)
            self.session.add(subrow)
            self.session.flush()

            for cell in cells:
                self.session.add(
                    NewProjectHa(
                        subrow_id=subrow.id,
                        season_id=season_map[cell.season],
                        hectareas=cell.hectareas,
                    )
                )

        self.session.commit()
        return orm.id

    def get(self, scenario_id: int) -> ScenarioState | None:
        """
        Carga el escenario completo con eager loading para evitar N+1 queries.

        Utiliza `selectinload` para cargar en batch todas las relaciones
        (temporadas, filas de tabla base, variedades y parámetros), reduciendo
        de ~14 queries a 6 queries por ciclo reactivo de Shiny.

        Args:
            scenario_id (int): Identificador del escenario a cargar.

        Returns:
            ScenarioState | None: Estado pydantic del escenario, o None si no existe.
        """
        # Eager loading en un solo round-trip para minimizar latencia en Supabase
        orm = (
            self.session.query(Scenario)
            .options(
                selectinload(Scenario.seasons),
                selectinload(Scenario.base_table_rows).selectinload(BaseTableRow.values),
                selectinload(Scenario.base_table_variation),
                selectinload(Scenario.varieties).selectinload(Variety.params),
                selectinload(Scenario.rules),
                selectinload(Scenario.new_project_groups)
                    .selectinload(NewProjectGroup.subrows)
                    .selectinload(NewProjectSubrow.ha_values),
            )
            .filter(Scenario.id == scenario_id)
            .first()
        )
        if orm is None:
            return None
        return _orm_to_pydantic_scenario(orm, self.session)

    def list_ids(self) -> list[tuple[int, str]]:
        rows = self.session.query(Scenario.id, Scenario.name).all()
        return [(r.id, r.name) for r in rows]

    def delete(self, scenario_id: int) -> bool:
        orm = self.session.get(Scenario, scenario_id)
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True


# ---------------------------------------------------------------------------
# RulesRepo
# ---------------------------------------------------------------------------


class RulesRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, scenario_id: int) -> PydanticRules | None:
        r = self.session.query(Rules).filter_by(scenario_id=scenario_id).first()
        if r is None:
            return None
        return PydanticRules(
            royaltie_fob=r.royaltie_fob,
            costo_plantines=r.costo_plantines,
            interes_financiamiento=r.interes_financiamiento,
            financiamiento_anios=r.financiamiento_anios,
        )

    def update(self, scenario_id: int, rules: PydanticRules) -> None:
        r = self.session.query(Rules).filter_by(scenario_id=scenario_id).first()
        if r is None:
            self.session.add(
                Rules(
                    scenario_id=scenario_id,
                    royaltie_fob=rules.royaltie_fob,
                    costo_plantines=rules.costo_plantines,
                    interes_financiamiento=rules.interes_financiamiento,
                    financiamiento_anios=rules.financiamiento_anios,
                )
            )
        else:
            r.royaltie_fob = rules.royaltie_fob
            r.costo_plantines = rules.costo_plantines
            r.interes_financiamiento = rules.interes_financiamiento
            r.financiamiento_anios = rules.financiamiento_anios
        self.session.commit()


# ---------------------------------------------------------------------------
# AuditRepo
# ---------------------------------------------------------------------------


class AuditRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log(
        self,
        entity: str,
        payload: dict[str, Any],
        scenario_id: int | None = None,
        entity_id: int | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                scenario_id=scenario_id,
                entity=entity,
                entity_id=entity_id,
                payload=payload,
            )
        )
        self.session.flush()
