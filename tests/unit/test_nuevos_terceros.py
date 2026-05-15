"""
Archivo: test_nuevos_terceros.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para la lógica del Bloque 3: Nuevos Terceros (T2.6). Valida
el proceso de agregación de hectáreas de productores externos (Talsa,
Diamond Bridge) y el cálculo de la rentabilidad de Hortifrut por conceptos
de comercialización y servicios, considerando las curvas de vida de la
variedad.

Acciones Principales:
    - Validación de la agregación de hectáreas por múltiples productores.
    - Verificación del cálculo de producción (miles de ton) por temporada.
    - Validación de la ganancia FOB para Hortifrut (comisión + diferencial).
    - Comprobación del aislamiento frente a bloques internos (B1, B2).

Estructura Interna:
    - `test_prod_año1_*`: Verifica la producción inicial de terceros.
    - `test_gan_año1_*`: Verifica el ingreso de HF por servicios a terceros.
    - `test_empty_cells_returns_zeros`: Asegura robustez ante entradas vacías.

Ejecución:
    pytest tests/unit/test_nuevos_terceros.py
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
from backend.logic.nuevos_terceros import compute_nuevos_terceros

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


# ha_agg B3 T2627 = Talsa(100) + Diamond Bridge(25) = 125
# ha_agg B3 T2728 = Talsa(100)

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


# --- A2.6.1 Producción ---


def test_prod_año1_t2728():
    """Año1 T2728: ha_agg[T2627]=125 × prod_hft[n=1]=13_000 / 1000 = 1_625."""
    s = _scenario(_B3_CELLS)
    result = compute_nuevos_terceros(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == pytest.approx(1_625.0, abs=1)


def test_prod_año1_t2829():
    """Año1 T2829: ha_agg[T2728]=100 × 13_000 / 1000 = 1_300."""
    s = _scenario(_B3_CELLS)
    result = compute_nuevos_terceros(s, _CALCULOS)
    # Año1 T2829 = ha[T2728]=100 × 13_000/1000 = 1_300
    # Año2 T2829 = ha[T2627]=125 × 19_500/1000 = 2_437.5
    # Total = 3_737.5
    assert result["V1"]["produccion"]["T2829"] == pytest.approx(3_737.5, abs=1)


# --- A2.6.2 Ganancia ---


def test_gan_año1_t2728():
    """Año1 T2728: 125 × (6_240 + 0) / 1000 = 780."""
    s = _scenario(_B3_CELLS)
    result = compute_nuevos_terceros(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T2728"] == pytest.approx(780.0, abs=1)


def test_gan_año4_t3132():
    """Año4 T3132: ha[T2728]=100 × (12_480 + 3_120) / 1000 = 1_560."""
    # n=4 pct=80% → prod_hft=32_500×0.8=26_000, prod_terc=32_500×0.2=6_500
    # gan_venta_propia_hft = 26_000×4×0.12=12_480
    # gan_venta_productor_hft = 6_500×4×0.12=3_120
    s = _scenario(_B3_CELLS)
    result = compute_nuevos_terceros(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T3132"] == pytest.approx(
        # Año4: ha[T2728]=100 × 15_600/1000 = 1_560
        # Año5: ha[T2627]=125 × 15_600/1000 = 1_950
        # Total T3132: 1_560 + 1_950 = 3_510
        3_510.0,
        abs=1,
    )


def test_b1_b2_cells_ignored():
    """Celdas de B1 y B2 no contribuyen a B3."""
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
    result = compute_nuevos_terceros(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0


def test_empty_cells_returns_zeros():
    s = _scenario([])
    result = compute_nuevos_terceros(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0
