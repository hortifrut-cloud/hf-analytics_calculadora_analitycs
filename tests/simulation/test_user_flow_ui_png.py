"""
Archivo: test_user_flow_ui_png.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Test de simulación de flujo de negocio (T2.10). Recrea el proceso de
cálculo completo para el escenario canónico "UI.png" y valida que los
totales de producción (fruta) y financieros (ganancia) coincidan
exactamente con los valores esperados definidos en los requerimientos.

Acciones Principales:
    - Validación de los subtotales de fruta para el bloque Hortifrut.
    - Validación de la ganancia neta consolidada por temporada.
    - Validación de los resultados de terceros (fruta y ganancia).
    - Verificación del determinismo del motor de cálculos consolidado.

Estructura Interna:
    - `test_hf_fruta`: Aserción contra valores golden de producción HF.
    - `test_hf_ganancia`: Aserción contra valores financieros HF.
    - `test_deterministic`: Asegura consistencia en ejecuciones repetidas.

Entradas / Dependencias:
    - `scenario_ui_png`: Fixture del escenario canónico definida en conftest.

Ejecución:
    pytest tests/simulation/test_user_flow_ui_png.py
"""

import json

import pytest

from backend.logic.recompute import recompute

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
TOL = 1.0

# Valores de UI.png sección 5 (Totales):
# HF_fruta T2728 = B1(3250) + B2(650) + B3_hft(1625) = 5525
# HF_ganancia T2728 = B1(13000) + B2(2600) + B3_hft(780) + plantines(568.75) = 16948.75

_HF_FRUTA_EXPECTED = {
    "T2627": 0.0,
    "T2728": 3250.0 + 650.0 + 1625.0,  # 5525
    "T2829": 7475.0 + 975.0 + 3737.5,  # 12187.5
    "T2930": 10400.0 + 1300.0 + 4875.0,  # 16575
    "T3031": 13325.0 + 1625.0 + 5590.0,  # 20540
    "T3132": 14625.0 + 1625.0 + 5443.75,  # 21693.75
}

_HF_GANANCIA_EXPECTED = {
    "T2627": 0.0,
    "T2728": 13000.0 + 2600.0 + 780.0 + 568.75,  # 16948.75
    "T2829": 29900.0 + 3900.0 + 1794.0 + 1023.75,  # 36617.75
    "T2930": 41600.0 + 5200.0 + 2496.0 + 1023.75,  # 50319.75
    "T3031": 53300.0 + 6500.0 + 3198.0 + 1023.75,  # 64021.75
    "T3132": 58500.0 + 6500.0 + 3510.0 + 1023.75,  # 69533.75
}

_TERCEROS_FRUTA_EXPECTED = {
    "T2627": 0.0,
    "T2728": 0.0,
    "T2829": 0.0,
    "T2930": 325.0,
    "T3031": 1072.5,
    "T3132": 1868.75,
}

_TERCEROS_GANANCIA_EXPECTED = {
    "T2627": 0.0,
    "T2728": 5720.0,
    "T2829": 13156.0,
    "T2930": 18304.0,
    "T3031": 23452.0,
    "T3132": 25740.0,
}


def test_hf_fruta(scenario_ui_png):
    result = recompute(scenario_ui_png)
    totales = result["totales"]
    for s in SEASONS:
        assert totales["hf_fruta"][s] == pytest.approx(
            _HF_FRUTA_EXPECTED[s], abs=TOL
        ), f"hf_fruta {s}"


def test_hf_ganancia(scenario_ui_png):
    result = recompute(scenario_ui_png)
    totales = result["totales"]
    for s in SEASONS:
        assert totales["hf_ganancia"][s] == pytest.approx(
            _HF_GANANCIA_EXPECTED[s], abs=TOL
        ), f"hf_ganancia {s}"


def test_terceros_fruta(scenario_ui_png):
    result = recompute(scenario_ui_png)
    totales = result["totales"]
    for s in SEASONS:
        assert totales["terceros_fruta"][s] == pytest.approx(
            _TERCEROS_FRUTA_EXPECTED[s], abs=TOL
        ), f"terceros_fruta {s}"


def test_terceros_ganancia(scenario_ui_png):
    result = recompute(scenario_ui_png)
    totales = result["totales"]
    for s in SEASONS:
        assert totales["terceros_ganancia"][s] == pytest.approx(
            _TERCEROS_GANANCIA_EXPECTED[s], abs=TOL
        ), f"terceros_ganancia {s}"


def test_deterministic(scenario_ui_png):
    """Dos llamadas a recompute sobre el mismo escenario producen el mismo resultado."""
    r1 = recompute(scenario_ui_png)
    r2 = recompute(scenario_ui_png)
    # Comparar sub-resultados numéricos (excluye calculos — dataclass no serializable)
    for key in (
        "crecimiento",
        "recambio",
        "nuevos_terceros",
        "plantines",
        "terceros_totales",
        "totales",
    ):
        assert r1[key] == r2[key], f"{key} no es determinístico"
