"""
Archivo: test_golden_imagen7_crecimiento.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Prueba de "Golden Master" para la lógica de Crecimiento HF (Sección 4.1). 
Valida que los cálculos de producción y ganancia coincidan con los valores 
de referencia definidos en `imagen7.csv`.

Acciones Principales:
    - Validación del subtotal de producción (toneladas) por temporada.
    - Validación del subtotal de ganancia (miles de USD) por temporada.
    - Uso de tolerancias para comparaciones de punto flotante.

Estructura Interna:
    - `test_subtotal_produccion`: Compara producción agregada contra golden.
    - `test_subtotal_ganancia`: Compara ganancia agregada contra golden.

Ejecución:
    pytest tests/golden/test_golden_imagen7_crecimiento.py
"""

import pytest

from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.crecimiento_hf import compute_crecimiento_hf

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
TOL = 1.0


def test_subtotal_produccion(scenario_ui_png, golden_imagen7):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_crecimiento_hf(scenario_ui_png, calculos)

    # Suma sobre todas las variedades
    subtotal = {s: sum(result[v]["produccion"][s] for v in result) for s in SEASONS}
    golden = golden_imagen7["Sub total (producción)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"produccion {season}"


def test_subtotal_ganancia(scenario_ui_png, golden_imagen7):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_crecimiento_hf(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["ganancia"][s] for v in result) for s in SEASONS}
    golden = golden_imagen7["Sub total (ganancia)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"ganancia {season}"
