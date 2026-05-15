"""Seeds — datos iniciales para el escenario canónico de UI.png.

`apply_defaults(session, scenario_id)` inserta Tabla Base y Reglas default.
"""

from sqlalchemy.orm import Session

from backend.db.repos import ScenarioRepo
from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow,
    NewProjectCell,
    Rules,
    ScenarioState,
    Variety,
    VarietyParamRow,
)

_SEASONS = ALL_SEASONS


def build_ui_png_scenario() -> ScenarioState:
    """Construye el ScenarioState canónico de UI.png (variedad V1)."""
    params = [
        VarietyParamRow(
            plant_year=y, productividad=p, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=r
        )
        for y, p, r in [
            (1, 2.0, 1.00),
            (2, 3.0, 1.00),
            (3, 4.0, 0.90),
            (4, 5.0, 0.80),
            (5, 5.0, 0.70),
            (6, 5.0, 0.60),
            (7, 5.0, 0.60),
        ]
    ]
    return ScenarioState(
        name="UI.png demo",
        base_table=BaseTable(
            rows=[
                BaseTableRow(
                    project_name="Trujillo",
                    unit="tn",
                    values={s: v for s, v in zip(_SEASONS, [37, 38, 39, 40, 41, 42])},
                    total=237.0,
                ),
                BaseTableRow(
                    project_name="Olmos",
                    unit="tn",
                    values={s: 8.0 for s in _SEASONS},
                    total=48.0,
                ),
                BaseTableRow(
                    project_name="Productores Terceros",
                    unit="tn",
                    values={s: v for s, v in zip(_SEASONS, [14, 15, 15, 15, 15, 15])},
                    total=89.0,
                ),
            ],
            variation={s: v for s, v in zip(_SEASONS, [-7, -7, -7, -7, -7, 0])},
        ),
        varieties=[Variety(name="V1", params=params)],
        rules=Rules(),
        new_project_cells=[
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            ),
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2728",
                hectareas=200,
            ),
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2627",
                hectareas=100,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2728",
                hectareas=100,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Diamond Bridge",
                variety_name="V1",
                season="T2627",
                hectareas=25,
            ),
        ],
    )


def seed_ui_png(session: Session) -> int:
    """Inserta el escenario canónico. Devuelve el ID creado."""
    repo = ScenarioRepo(session)
    return repo.create(build_ui_png_scenario())
