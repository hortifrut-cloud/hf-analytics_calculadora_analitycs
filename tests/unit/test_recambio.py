"""Tests unitarios — backend/logic/recambio.py (T2.5)."""

import pytest

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
from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.recambio import compute_recambio

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]

_PARAMS = [
    VarietyParamRow(
        plant_year=y, productividad=p, densidad=6500, precio_estimado=4.0, pct_recaudacion=r
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
_V1 = Variety(name="V1", params=_PARAMS)
_RULES = Rules()
_CALCULOS = compute_calculos_variedades([_V1], _RULES)

_BASE_TABLE = BaseTable(
    rows=[BaseTableRow(project_name="P1", unit="tn", values={s: 0.0 for s in SEASONS}, total=0.0)],
    variation={s: 0.0 for s in SEASONS},
)


def _scenario(cells):
    return ScenarioState(
        name="test",
        base_table=_BASE_TABLE,
        varieties=[_V1],
        rules=_RULES,
        new_project_cells=cells,
    )


# --- A2.5.1 — imagen8: OLMOS 50ha@T2627 ---


def test_prod_año1_t2728_olmos50():
    """OLMOS 50ha@T2627 → Año1 T2728: 50 × 13_000 / 1000 = 650."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == pytest.approx(650.0, abs=1)


def test_prod_año2_t2829_olmos50():
    """OLMOS 50ha@T2627 → Año2 T2829: 50 × 19_500 / 1000 = 975."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2829"] == pytest.approx(975.0, abs=1)


def test_gan_año1_t2728_olmos50():
    """OLMOS 50ha@T2627 → Año1 T2728: 50 × 52_000 / 1000 = 2_600."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T2728"] == pytest.approx(2_600.0, abs=1)


def test_gan_año2_t2829_olmos50():
    """OLMOS 50ha@T2627 → Año2 T2829: 50 × (4×6500×3) / 1000 = 50×78_000/1000 = 3_900."""
    # gan_hfi año2 = 4 × 6500 × 3 = 78_000
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T2829"] == pytest.approx(3_900.0, abs=1)


def test_t2627_is_zero():
    """T2627 es 0 — no puede haber cosecha el mismo año de siembra."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2627"] == 0.0


def test_b1_cells_ignored():
    """Celdas B1 no contribuyen a B2."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=999,
            )
        ]
    )
    result = compute_recambio(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == 0.0


def test_empty_cells_returns_zeros():
    """Sin celdas B2 → todos cero."""
    s = _scenario([])
    result = compute_recambio(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0
