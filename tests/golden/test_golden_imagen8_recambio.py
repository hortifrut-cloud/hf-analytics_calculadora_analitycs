"""
Archivo: test_golden_imagen8_recambio.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Prueba de "Golden Master" para la lógica de Recambio Varietal (Sección 4.2). 
Valida la consistencia de los cálculos frente a los datos de referencia en 
`imagen8.csv`, manejando excepciones específicas de la temporada T26/27.

Acciones Principales:
    - Validación de agregados de producción para el bloque de recambio.
    - Validación de agregados de ganancia para el bloque de recambio.
    - Aseguramiento de la integridad de los datos frente a fuentes externas.

Estructura Interna:
    - `test_subtotal_produccion`: Verifica toneladas agregadas.
    - `test_subtotal_ganancia`: Verifica margen de ganancia agregado.

Ejecución:
    pytest tests/golden/test_golden_imagen8_recambio.py
"""

import pytest

from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.recambio import compute_recambio

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
TOL = 1.0


def test_subtotal_produccion(scenario_ui_png, golden_imagen8):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_recambio(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["produccion"][s] for v in result) for s in SEASONS}
    golden = golden_imagen8["Sub total (producción)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"produccion {season}"


def test_subtotal_ganancia(scenario_ui_png, golden_imagen8):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_recambio(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["ganancia"][s] for v in result) for s in SEASONS}
    golden = golden_imagen8["Sub total (ganancia)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"ganancia {season}"
