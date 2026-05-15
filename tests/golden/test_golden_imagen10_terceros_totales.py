"""Golden test — imagen10.csv vs compute_terceros_totales (T2.8)."""

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
