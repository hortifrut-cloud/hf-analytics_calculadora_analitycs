"""
Archivo: test_golden_imagen10_terceros_totales.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Prueba de "Golden Master" para la lógica consolidada de Terceros (Sección 4.5). 
Valida los resultados finales de producción y ganancia para el bloque de 
terceros contra la referencia `imagen10.csv`. Incluye validaciones de 
independencia entre bloques (bloque 3 no afectado por bloques 1 y 2).

Acciones Principales:
    - Validación de agregados finales de producción para terceros.
    - Validación de agregados finales de ganancia para terceros.
    - Test de aislamiento: asegura que cambios en B1/B2 no alteran los totales de B3.

Estructura Interna:
    - `test_subtotal_produccion`: Verifica toneladas totales de terceros.
    - `test_subtotal_ganancia`: Verifica margen de ganancia total de terceros.
    - `test_b1_b2_not_included`: Valida la lógica de filtrado por bloque.

Ejecución:
    pytest tests/golden/test_golden_imagen10_terceros_totales.py
"""

import pytest

from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.terceros_totales import compute_terceros_totales

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
TOL = 1.0


def test_subtotal_produccion(scenario_ui_png, golden_imagen10):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_terceros_totales(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["produccion"][s] for v in result) for s in SEASONS}
    golden = golden_imagen10["Sub total (producción)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"produccion {season}"


def test_subtotal_ganancia(scenario_ui_png, golden_imagen10):
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    result = compute_terceros_totales(scenario_ui_png, calculos)

    subtotal = {s: sum(result[v]["ganancia"][s] for v in result) for s in SEASONS}
    golden = golden_imagen10["Sub total (ganancia)"]

    for season in SEASONS:
        assert subtotal[season] == pytest.approx(golden[season], abs=TOL), f"ganancia {season}"


def test_b1_b2_not_included(scenario_ui_png):
    """Modificar B1/B2 no cambia el resultado — solo B3 cuenta."""
    from backend.domain.enums import BloqueKind
    from backend.domain.inputs import NewProjectCell, ScenarioState

    # Escenario sin celdas B1/B2 → mismo resultado
    cells_b3_only = [
        c for c in scenario_ui_png.new_project_cells if c.bloque == BloqueKind.NUEVOS_TERCEROS
    ]
    scenario_b3_only = ScenarioState(
        name=scenario_ui_png.name,
        base_table=scenario_ui_png.base_table,
        varieties=scenario_ui_png.varieties,
        rules=scenario_ui_png.rules,
        new_project_cells=cells_b3_only,
    )
    calculos = compute_calculos_variedades(list(scenario_ui_png.varieties), scenario_ui_png.rules)
    r_full = compute_terceros_totales(scenario_ui_png, calculos)
    r_b3 = compute_terceros_totales(scenario_b3_only, calculos)

    assert r_full == r_b3
