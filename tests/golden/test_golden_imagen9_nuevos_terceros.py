"""
Archivo: test_golden_imagen9_nuevos_terceros.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Prueba de "Golden Master" para la lógica de Nuevos Terceros y Plantines 
(Secciones 4.3 y 4.4). Valida los cálculos de producción, ganancia de fruta 
y ganancia por venta de plantines contra la referencia `imagen9.csv`.

Acciones Principales:
    - Validación de subtotal de producción para el bloque de terceros.
    - Validación de subtotal de ganancia para el bloque de terceros.
    - Validación de ingresos por venta de plantines (regalías y margen).

Estructura Interna:
    - `test_subtotal_produccion`: Compara producción de terceros.
    - `test_subtotal_ganancia`: Compara margen de ganancia de terceros.
    - `test_subtotal_ganancia_plantines`: Compara ingresos por plantines.

Ejecución:
    pytest tests/golden/test_golden_imagen9_nuevos_terceros.py
"""

import pytest

from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.nuevos_terceros import compute_nuevos_terceros
from backend.logic.plantines import compute_plantines

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
TOL = 1.0


def test_subtotal_produccion(scenario_ui_png, golden_imagen9):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_nuevos_terceros(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["produccion"][s] for v in result) for s in SEASONS}
    golden = golden_imagen9["Sub total (producción)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"produccion {season}"


def test_subtotal_ganancia(scenario_ui_png, golden_imagen9):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_nuevos_terceros(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["ganancia"][s] for v in result) for s in SEASONS}
    golden = golden_imagen9["Sub total (ganancia)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"ganancia {season}"


def test_subtotal_ganancia_plantines(scenario_ui_png, golden_imagen9):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_plantines(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v][s] for v in result) for s in SEASONS}
    golden = golden_imagen9["Sub total (ganancia plantines)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"plantines {season}"
