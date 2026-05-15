import logging

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

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]

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


def _make_base_table() -> BaseTable:
    return BaseTable(
        rows=[
            BaseTableRow(
                project_name="CHAO",
                unit="ton",
                values={s: 0.0 for s in SEASONS},
                total=0.0,
            )
        ],
        variation={s: 0.0 for s in SEASONS},
    )


def _base_cells() -> list[NewProjectCell]:
    return [
        NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="CHAO",
            variety_name="V1",
            season="T2627",
            hectareas=250,
        )
    ]


def _make_scenario(**overrides: object) -> ScenarioState:
    defaults: dict[str, object] = dict(
        name="test",
        base_table=_make_base_table(),
        varieties=[Variety(name="V1", params=V1_PARAMS)],
        rules=Rules(),
        new_project_cells=_base_cells(),
    )
    defaults.update(overrides)
    return ScenarioState(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# A1.4.1 — Validador: variedades referenciadas existen
# ---------------------------------------------------------------------------


def test_unknown_variety_name_fails() -> None:
    bad_cell = NewProjectCell(
        bloque=BloqueKind.CRECIMIENTO_HF,
        sub_proyecto="CHAO",
        variety_name="INEXISTENTE",
        season="T2627",
        hectareas=100,
    )
    with pytest.raises(ValidationError, match="'INEXISTENTE' no existe en el escenario"):
        _make_scenario(new_project_cells=[bad_cell])


def test_known_variety_name_ok() -> None:
    s = _make_scenario()
    assert s.new_project_cells[0].variety_name == "V1"


# ---------------------------------------------------------------------------
# A1.4.2 — Validador: temporadas dentro del rango
# ---------------------------------------------------------------------------


def test_invalid_season_fails() -> None:
    # SeasonCode Literal prevents this at field level, but we also check cross-field.
    # We bypass Literal by using model_construct on the cell, then pass to ScenarioState.
    bad_cell = NewProjectCell.model_construct(
        bloque=BloqueKind.CRECIMIENTO_HF,
        sub_proyecto="CHAO",
        variety_name="V1",
        season="T2526",  # fuera de rango
        hectareas=100,
    )
    with pytest.raises(ValidationError, match="fuera del rango"):
        _make_scenario(new_project_cells=[bad_cell])


def test_valid_season_ok() -> None:
    for season in ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]:
        cell = NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="CHAO",
            variety_name="V1",
            season=season,  # type: ignore[arg-type]
            hectareas=10,
        )
        s = _make_scenario(new_project_cells=[cell])
        assert s.new_project_cells[0].season == season


# ---------------------------------------------------------------------------
# A1.4.3 — Validador: sub-proyectos por bloque (warn, no error)
# ---------------------------------------------------------------------------


def test_unknown_subproyecto_b1_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    cell = NewProjectCell(
        bloque=BloqueKind.CRECIMIENTO_HF,
        sub_proyecto="NUEVO_CAMPO",
        variety_name="V1",
        season="T2627",
        hectareas=50,
    )
    with caplog.at_level(logging.WARNING, logger="backend.domain.inputs"):
        s = _make_scenario(new_project_cells=[cell])
    assert s.new_project_cells[0].sub_proyecto == "NUEVO_CAMPO"
    assert any("NUEVO_CAMPO" in r.message for r in caplog.records)


def test_unknown_subproyecto_b3_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    cell = NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS,
        sub_proyecto="CAMPO_RARO",
        variety_name="V1",
        season="T2627",
        hectareas=50,
    )
    with caplog.at_level(logging.WARNING, logger="backend.domain.inputs"):
        s = _make_scenario(new_project_cells=[cell])
    assert s.new_project_cells[0].sub_proyecto == "CAMPO_RARO"
    assert any("CAMPO_RARO" in r.message for r in caplog.records)


def test_known_subproyecto_b3_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    cell = NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS,
        sub_proyecto="Talsa",
        variety_name="V1",
        season="T2627",
        hectareas=100,
    )
    with caplog.at_level(logging.WARNING, logger="backend.domain.inputs"):
        _make_scenario(new_project_cells=[cell])
    assert not any("Talsa" in r.message for r in caplog.records)
