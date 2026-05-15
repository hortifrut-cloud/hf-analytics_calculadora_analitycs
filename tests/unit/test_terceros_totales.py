"""
Archivo: test_terceros_totales.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para la lógica de consolidación de terceros (T2.8).
Valida la segregación entre la producción retenida por el tercero y la
producción comercializada por Hortifrut, asegurando que los ingresos por
ventas y servicios se calculen según el porcentaje de recaudación pactado.

Acciones Principales:
    - Validación de la producción neta de terceros (miles de ton).
    - Verificación del cálculo de ingresos por comercialización externa.
    - Validación de la invariante de producción cero en Año 1 (recaudación=1).
    - Comprobación del aislamiento frente a bloques internos (B1, B2).

Estructura Interna:
    - `test_prod_año3_*`: Verifica el rendimiento consolidado de terceros.
    - `test_gan_año1_*`: Verifica la comisión de venta de Hortifrut.
    - `test_b1_b2_cells_ignored`: Garantiza que B3 sea independiente.

Ejecución:
    pytest tests/unit/test_terceros_totales.py
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
from backend.logic.terceros_totales import compute_terceros_totales

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


def _scenario(cells):
    return ScenarioState(
        name="test",
        base_table=_BASE_TABLE,
        varieties=[_V1],
        rules=_RULES,
        new_project_cells=cells,
    )


def test_prod_año1_t2728_es_cero():
    """Año1 pct_recaud=1.0 → prod_terceros=0 → producción=0."""
    s = _scenario(_B3_CELLS)
    result = compute_terceros_totales(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2728"] == 0.0


def test_prod_año3_t2930():
    """Año3 T2930: ha[T2627]=125 × prod_terceros[3] / 1000.
    prod_hfi[3]=26000, pct=0.90 → prod_terceros=2600.
    125 × 2600 / 1000 = 325.
    """
    s = _scenario(_B3_CELLS)
    result = compute_terceros_totales(s, _CALCULOS)
    assert result["V1"]["produccion"]["T2930"] == pytest.approx(325.0, abs=1)


def test_gan_año1_t2728():
    """Año1 T2728: ha[T2627]=125 × (gan_venta_hf + gan_venta_propia_terceros) / 1000.
    gan_venta_hf_terceros = 13000×4×0.88=45760, gan_venta_propia_terceros=0.
    125 × 45760 / 1000 = 5720.
    """
    s = _scenario(_B3_CELLS)
    result = compute_terceros_totales(s, _CALCULOS)
    assert result["V1"]["ganancia"]["T2728"] == pytest.approx(5720.0, abs=1)


def test_b1_b2_cells_ignored():
    """Celdas B1/B2 no contribuyen."""
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
    result = compute_terceros_totales(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0


def test_empty_cells_returns_zeros():
    s = _scenario([])
    result = compute_terceros_totales(s, _CALCULOS)
    for season in SEASONS:
        assert result["V1"]["produccion"][season] == 0.0
        assert result["V1"]["ganancia"][season] == 0.0
