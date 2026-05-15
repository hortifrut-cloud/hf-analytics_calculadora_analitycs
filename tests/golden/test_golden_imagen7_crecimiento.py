"""Golden test — imagen7.csv vs compute_crecimiento_hf (T2.4 A2.4.2)."""

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
