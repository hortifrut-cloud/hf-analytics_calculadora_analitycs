"""Golden test — imagen9.csv vs compute_nuevos_terceros + compute_plantines (T2.6, T2.7)."""

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
