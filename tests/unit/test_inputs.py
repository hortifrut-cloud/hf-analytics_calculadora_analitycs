import pytest
from pydantic import ValidationError

from backend.domain.enums import BloqueKind
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow,
    NewProjectCell,
    Rules,
    ScenarioState,
    Variety,
    VarietyParamRow,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

V1_PARAMS = [
    VarietyParamRow(
        plant_year=y,
        productividad=prod,
        densidad=6500,
        precio_estimado=4.0,
        pct_recaudacion=pct,
    )
    for y, prod, pct in [
        (1, 2.0, 1.00),
        (2, 3.0, 1.00),
        (3, 4.0, 0.90),
        (4, 5.0, 0.80),
        (5, 5.0, 0.70),
        (6, 5.0, 0.60),
        (7, 5.0, 0.60),
    ]
]

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]


def _make_base_table() -> BaseTable:
    return BaseTable(
        rows=[
            BaseTableRow(
                project_name="CHAO",
                unit="ton",
                values={s: float(v) for s, v in zip(SEASONS, [37, 0, 0, 0, 0, 0])},
                total=37.0,
            ),
            BaseTableRow(
                project_name="OLMOS",
                unit="ton",
                values={s: float(v) for s, v in zip(SEASONS, [0, 26, 0, 0, 0, 0])},
                total=26.0,
            ),
            BaseTableRow(
                project_name="Talsa/Diamond Bridge",
                unit="ton",
                values={s: float(v) for s, v in zip(SEASONS, [0, 0, 0, 0, 0, 0])},
                total=0.0,
            ),
        ],
        variation={s: 0.0 for s in SEASONS},
    )


def _make_scenario() -> ScenarioState:
    return ScenarioState(
        name="UI.png demo",
        base_table=_make_base_table(),
        varieties=[Variety(name="V1", params=V1_PARAMS)],
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
                season="T2728",
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


# ---------------------------------------------------------------------------
# A1.2.1 — BaseTable
# ---------------------------------------------------------------------------


def test_base_table_row_total_ok() -> None:
    row = BaseTableRow(
        project_name="X",
        unit="ton",
        values={"T2627": 10.0, "T2728": 20.0},
        total=30.0,
    )
    assert row.total == 30.0


def test_base_table_row_total_tolerance() -> None:
    # Within tolerance of 1
    row = BaseTableRow(
        project_name="X",
        unit="ton",
        values={"T2627": 10.3, "T2728": 20.4},
        total=31.0,
    )
    assert row.total == 31.0


def test_base_table_row_total_fails_outside_tolerance() -> None:
    with pytest.raises(ValidationError, match="difiere"):
        BaseTableRow(
            project_name="X",
            unit="ton",
            values={"T2627": 10.0, "T2728": 20.0},
            total=35.0,
        )


# ---------------------------------------------------------------------------
# A1.2.2 — Variety
# ---------------------------------------------------------------------------


def test_variety_v1_canonical() -> None:
    v = Variety(name="V1", params=V1_PARAMS)
    assert len(v.params) == 7
    assert v.params[0].productividad == 2.0
    assert v.params[4].pct_recaudacion == 0.70


def test_variety_missing_year_fails() -> None:
    params_6 = [p for p in V1_PARAMS if p.plant_year != 7]
    with pytest.raises(ValidationError, match="1..7"):
        Variety(name="V1", params=params_6)


def test_variety_extra_year_fails() -> None:
    duplicate = VarietyParamRow(
        plant_year=1, productividad=2.0, densidad=6500, precio_estimado=4.0, pct_recaudacion=1.0
    )
    with pytest.raises(ValidationError, match="duplicados"):
        Variety(name="V1", params=V1_PARAMS + [duplicate])


def test_variety_empty_name_fails() -> None:
    with pytest.raises(ValidationError):
        Variety(name="", params=V1_PARAMS)


# ---------------------------------------------------------------------------
# A1.2.3 — Rules
# ---------------------------------------------------------------------------


def test_rules_defaults() -> None:
    r = Rules()
    assert r.royaltie_fob == 0.12
    assert r.costo_plantines == 3.5
    assert r.interes_financiamiento == 0.0
    assert r.financiamiento_anios == 5


def test_rules_custom() -> None:
    r = Rules(royaltie_fob=0.20, financiamiento_anios=3)
    assert r.royaltie_fob == 0.20
    assert r.financiamiento_anios == 3


def test_rules_royaltie_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Rules(royaltie_fob=1.5)


# ---------------------------------------------------------------------------
# A1.2.4 — NewProjectCell
# ---------------------------------------------------------------------------


def test_new_project_cell_valid() -> None:
    c = NewProjectCell(
        bloque=BloqueKind.CRECIMIENTO_HF,
        sub_proyecto="CHAO",
        variety_name="V1",
        season="T2627",
        hectareas=250,
    )
    assert c.hectareas == 250


def test_new_project_cell_negative_ha_fails() -> None:
    with pytest.raises(ValidationError):
        NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="CHAO",
            variety_name="V1",
            season="T2627",
            hectareas=-10,
        )


# ---------------------------------------------------------------------------
# A1.2.5 — ScenarioState
# ---------------------------------------------------------------------------


def test_scenario_state_builds() -> None:
    s = _make_scenario()
    assert s.name == "UI.png demo"
    assert len(s.varieties) == 1
    assert len(s.new_project_cells) == 6


def test_scenario_state_frozen() -> None:
    s = _make_scenario()
    with pytest.raises(ValidationError):
        s.name = "other"  # type: ignore[misc]


def test_scenario_state_json_deterministic() -> None:
    s = _make_scenario()
    j1 = s.model_dump_json()
    j2 = s.model_dump_json()
    assert j1 == j2
