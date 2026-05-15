"""
Archivo: test_crecimiento_hf.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para la lógica del Bloque 1: Crecimiento HF (T2.4). Valida
que la siembra de nuevas hectáreas por parte de Hortifrut se traduzca en
la producción y ganancia esperada a lo largo de las temporadas,
considerando el desfase temporal (*shift*) inherente al crecimiento de la
planta.

Acciones Principales:
    - Validación de producción individual por proyecto (Chao, Olmos).
    - Verificación de la agregación de múltiples siembras en una misma temporada.
    - Validación de la invariante de temporada 0 (T2627) siempre en cero.
    - Comprobación del aislamiento de celdas (ignorar bloques ajenos a B1).

Estructura Interna:
    - `test_prod_año1_*`: Verifica el primer año de cosecha tras la siembra.
    - `test_prod_t2829_*`: Verifica la suma de plantas en diferentes edades.
    - `test_b3_cells_ignored`: Garantiza que el bloque sea puro y no se contamine.

Ejecución:
    pytest tests/unit/test_crecimiento_hf.py
"""

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
from backend.logic.crecimiento_hf import compute_crecimiento_hf

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


# --- A2.4.1 producción individual ---


def test_prod_año1_t2728_chao250():
    """CHAO 250ha@T2627 → Año1 T2728: 250 × 13_000 / 1000 = 3_250."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            )
        ]
    )
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == pytest.approx(3_250.0, abs=1)


def test_prod_año5_t3132_chao250():
    """CHAO 250ha@T2627 → Año5 T3132: 250 × 32_500 / 1000 = 8_125."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            )
        ]
    )
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["produccion"]["T3132"] == pytest.approx(8_125.0, abs=1)


def test_prod_t2829_chao250_olmos200():
    """T2829 = Año1(OLMOS 200ha) + Año2(CHAO 250ha) = 2_600 + 4_950 = 7_550... verify against formula."""
    # Año1 T2829: OLMOS 200ha × 13_000 / 1000 = 2_600
    # Año2 T2829: CHAO 250ha × (3×6500) / 1000 = 250 × 19_500 / 1000 = 4_875
    # Total = 7_475
    cells = [
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
    ]
    s = _scenario(cells)
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2829"] == pytest.approx(7_475.0, abs=1)


def test_gan_año1_t2728_chao250():
    """CHAO 250ha@T2627 → Año1 T2728: 250 × 52_000 / 1000 = 13_000."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            )
        ]
    )
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T2728"] == pytest.approx(13_000.0, abs=1)


def test_t2627_always_zero():
    """T2627 siempre 0 porque no hay cosecha en temporada 0 (shift)."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            )
        ]
    )
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2627"] == 0.0
    assert result["V1"]["ganancia"]["T2627"] == 0.0


def test_empty_cells_returns_zeros():
    """Sin celdas B1 → todos cero."""
    s = _scenario([])
    result = compute_crecimiento_hf(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0


def test_b3_cells_ignored():
    """Celdas B3 no contribuyen a B1."""
    s = _scenario(
        [
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2627",
                hectareas=999,
            )
        ]
    )
    result = compute_crecimiento_hf(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == 0.0
