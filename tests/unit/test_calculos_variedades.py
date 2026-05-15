"""
Archivo: test_calculos_variedades.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para la lógica de pre-cálculo de variedades (T2.2). Valida
que las métricas base (producción y ganancia) para los bloques HFI, HFT y
Terceros se calculen correctamente por cada año de vida de la planta,
considerando densidades, productividades y porcentajes de recaudación.

Acciones Principales:
    - Validación de producción y ganancia interna (HFI).
    - Validación de métricas para venta propia y productor en HFT.
    - Validación de producción y ganancia para el bloque de Terceros.
    - Verificación de la cobertura completa de los 7 años de vida.

Estructura Interna:
    - `calculos`: Fixture que genera la matriz de pre-cálculo para V1.
    - `test_hfi_*`: Validaciones del bloque Hortifrut Interna.
    - `test_hft_*`: Validaciones del bloque Hortifrut Terceros.

Ejecución:
    pytest tests/unit/test_calculos_variedades.py
"""

import pytest

from backend.domain.inputs import Rules, Variety, VarietyParamRow
from backend.logic.calculos_variedades import compute_calculos_variedades

V1_PARAMS = [
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
V1 = Variety(name="V1", params=V1_PARAMS)
RULES = Rules()


@pytest.fixture(scope="module")
def calculos():
    return compute_calculos_variedades([V1], RULES)


# A2.2.1 — HF Interna
def test_hfi_año1_prod(calculos):
    row = calculos[("V1", 1)]
    assert row.prod_hfi == 2 * 6500  # 13_000


def test_hfi_año1_gan(calculos):
    row = calculos[("V1", 1)]
    assert row.gan_hfi == 4 * 13_000  # 52_000


def test_hfi_año5_prod(calculos):
    row = calculos[("V1", 5)]
    assert row.prod_hfi == 5 * 6500  # 32_500


# A2.2.2 — HF Terceros
def test_hft_año1_prod(calculos):
    # pct_recaud=100% → prod_hft = prod_hfi × 1.0
    row = calculos[("V1", 1)]
    assert row.prod_hft == 13_000


def test_hft_año1_gan_venta_propia(calculos):
    # 13_000 × 4 × 0.12 = 6_240
    row = calculos[("V1", 1)]
    assert row.gan_venta_propia_hft == pytest.approx(6_240.0)


def test_hft_año1_gan_venta_productor(calculos):
    # ProdTerceros=0 → ganancia productor=0
    row = calculos[("V1", 1)]
    assert row.gan_venta_productor_hft == pytest.approx(0.0)


def test_hft_año5_prod(calculos):
    # pct=70% → 32_500 × 0.70 = 22_750
    row = calculos[("V1", 5)]
    assert row.prod_hft == pytest.approx(22_750.0)


def test_hft_año5_gan_venta_propia(calculos):
    # 22_750 × 4 × 0.12 = 10_920
    row = calculos[("V1", 5)]
    assert row.gan_venta_propia_hft == pytest.approx(10_920.0)


def test_hft_año5_gan_venta_productor(calculos):
    # ProdTerceros = 32_500 × 0.30 = 9_750 → 9_750 × 4 × 0.12 = 4_680
    row = calculos[("V1", 5)]
    assert row.gan_venta_productor_hft == pytest.approx(4_680.0)


# A2.2.3 — Terceros
def test_terceros_año5_prod(calculos):
    # 32_500 × 0.30 = 9_750
    row = calculos[("V1", 5)]
    assert row.prod_terceros == pytest.approx(9_750.0)


def test_terceros_año1_gan_venta_hf(calculos):
    # prod_hft=13_000 × 4 × (1-0.12) = 45_760
    row = calculos[("V1", 1)]
    assert row.gan_venta_hf_terceros == pytest.approx(45_760.0)


def test_terceros_año5_gan_total(calculos):
    # (22_750 + 9_750) × 4 × 0.88 = 32_500 × 4 × 0.88 = 114_400
    row = calculos[("V1", 5)]
    total = row.gan_venta_hf_terceros + row.gan_venta_propia_terceros
    assert total == pytest.approx(114_400.0)


# A2.2.4 — todos los años cubiertos
def test_all_years_present(calculos):
    for n in range(1, 8):
        assert ("V1", n) in calculos
