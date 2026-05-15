"""Tests unitarios — backend/logic/plantines.py (T2.7)."""

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
from backend.logic.plantines import compute_plantines, cuota_amortizacion

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
_RULES = Rules()  # financiamiento_anios=5, costo_plantines=3.5
_CALCULOS = compute_calculos_variedades([_V1], _RULES)

_BASE_TABLE = BaseTable(
    rows=[BaseTableRow(project_name="P1", unit="tn", values={s: 0.0 for s in SEASONS}, total=0.0)],
    variation={s: 0.0 for s in SEASONS},
)


def _scenario(cells, rules=None):
    return ScenarioState(
        name="test",
        base_table=_BASE_TABLE,
        varieties=[_V1],
        rules=rules or _RULES,
        new_project_cells=cells,
    )


_B3_CELLS = [
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
]


# --- A2.7.3 hook cuota_amortizacion ---


def test_cuota_amortizacion_con_interes():
    """cuota(1000, 0.10, 5) ≈ 263.80."""
    assert cuota_amortizacion(1000.0, 0.10, 5) == pytest.approx(263.797, abs=0.01)


def test_cuota_amortizacion_sin_interes():
    """cuota(1000, 0.0, 5) = 200."""
    assert cuota_amortizacion(1000.0, 0.0, 5) == pytest.approx(200.0)


# --- A2.7.1 Fórmula base ---


def test_plantines_año1_t2728():
    """Año1 T2728: ha_agg[T2627]=125 × 6500 × 3.5 / 5 / 1000 = 568.75."""
    s = _scenario(_B3_CELLS)
    result = compute_plantines(s, _CALCULOS)
    assert result["V1"]["T2728"] == pytest.approx(568.75, abs=0.01)


def test_plantines_año2_t2829():
    """Año2 T2829 = Año1(ha[T2728]=100) + Año2(ha[T2627]=125)."""
    # Año1 T2829: ha[T2728]=100 × 6500 × 3.5 / 5 / 1000 = 455.0
    # Año2 T2829: ha[T2627]=125 × 6500 × 3.5 / 5 / 1000 = 568.75
    # Total = 1_023.75
    s = _scenario(_B3_CELLS)
    result = compute_plantines(s, _CALCULOS)
    assert result["V1"]["T2829"] == pytest.approx(1_023.75, abs=0.01)


def test_t2627_always_zero():
    """T2627 = 0 (sin ha en temporadas anteriores)."""
    s = _scenario(_B3_CELLS)
    result = compute_plantines(s, _CALCULOS)
    assert result["V1"]["T2627"] == 0.0


# --- A2.7.2 Máscara de truncamiento ---


def test_mascara_financiamiento_defecto_5():
    """Con financiamiento=5, años n=1..5 contribuyen; n=6,7 no."""
    # Siembra única en T2627 → contribuye desde T2628 hasta T3132 (5 saltos)
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2627",
                hectareas=100,
            )
        ]
    )
    result = compute_plantines(s, _CALCULOS)
    # T3132 = n=6 shift desde T2627 → va más allá del horizonte de 6 temporadas
    # En la lista T2627..T3132 hay 6 estaciones. Shift de 6 → T3132 viene de antes de T2627 = 0
    # Pero n=6 > financiamiento_anios=5 → máscara lo descarta igualmente
    # n=5: shift 5 desde T2627 → T3132; contribuye 100×6500×3.5/5/1000 = 455
    assert result["V1"]["T3132"] == pytest.approx(455.0, abs=0.01)


def test_mascara_financiamiento_3():
    """Con financiamiento=3, años n=4..7 son 0 para siembra en T2627."""
    rules3 = Rules(financiamiento_anios=3)
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2627",
                hectareas=100,
            )
        ],
        rules=rules3,
    )
    result = compute_plantines(s, _CALCULOS)
    # n=1→T2728, n=2→T2829, n=3→T2930 contribuyen
    # n=4→T3031, n=5→T3132 deben ser 0 por máscara (n > 3)
    assert result["V1"]["T3031"] == pytest.approx(0.0, abs=0.01)
    assert result["V1"]["T3132"] == pytest.approx(0.0, abs=0.01)
    # T2728 debe tener valor: 100 × 6500 × 3.5 / 3 / 1000
    assert result["V1"]["T2728"] == pytest.approx(100 * 6500 * 3.5 / 3 / 1000, abs=0.01)


def test_b1_b2_cells_not_used_for_plantines():
    """Celdas B1 y B2 no generan plantines."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=999,
            ),
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=999,
            ),
        ]
    )
    result = compute_plantines(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"][season] == 0.0
