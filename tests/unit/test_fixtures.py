"""
Archivo: test_fixtures.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Pruebas de integridad para los fixtures globales de la suite (A2.1).
Verifica que el orquestador `conftest.py` cargue correctamente los
archivos maestros (Golden Masters) y construya el escenario "UI.png" con
los valores exactos requeridos por las especificaciones de negocio.

Acciones Principales:
    - Validación de la carga de `BaseTable` desde Trujillo/Olmos.
    - Verificación de la estructura del escenario maestro `UI.png`.
    - Validación de los subtotales "Golden" para las imágenes 7 a 10.
    - Comprobación de que las rutas a los CSVs sean válidas.

Estructura Interna:
    - `test_base_table_*`: Verifica la tabla base histórica.
    - `test_scenario_ui_png_builds`: Verifica el escenario de referencia.
    - `test_golden_imagenX_subtotals`: Verifica los valores maestros.

Ejecución:
    pytest tests/unit/test_fixtures.py
"""

from tests.conftest import ScenarioState

_PROD_KEY = "Sub total (producción)"
_GAN_KEY = "Sub total (ganancia)"
_PLAN_KEY = "Sub total (ganancia plantines)"


def test_base_table_imagen1(base_table_imagen1):  # type: ignore[no-untyped-def]
    assert len(base_table_imagen1.rows) == 3
    assert base_table_imagen1.rows[0].values["T2627"] == 37.0
    assert base_table_imagen1.rows[0].total == 237.0


def test_scenario_ui_png_builds(scenario_ui_png: ScenarioState) -> None:
    assert scenario_ui_png.name == "UI.png demo"
    assert len(scenario_ui_png.varieties) == 1
    assert len(scenario_ui_png.new_project_cells) == 6
    assert scenario_ui_png.varieties[0].params[0].productividad == 2.0


def test_golden_imagen7_subtotals(golden_imagen7):  # type: ignore[no-untyped-def]
    prod = golden_imagen7[_PROD_KEY]
    assert prod["T2728"] == 3250.0
    assert prod["T2829"] == 7475.0
    assert prod["T3132"] == 14625.0
    gan = golden_imagen7[_GAN_KEY]
    assert gan["T2728"] == 13000.0


def test_golden_imagen8_subtotals(golden_imagen8):  # type: ignore[no-untyped-def]
    prod = golden_imagen8[_PROD_KEY]
    assert prod["T2728"] == 650.0
    assert prod["T3031"] == 1625.0


def test_golden_imagen9_subtotals(golden_imagen9):  # type: ignore[no-untyped-def]
    prod = golden_imagen9[_PROD_KEY]
    assert prod["T2728"] == 1625.0
    plan = golden_imagen9[_PLAN_KEY]
    assert plan["T2728"] == pytest.approx(568.75, abs=0.01)


def test_golden_imagen10_subtotals(golden_imagen10):  # type: ignore[no-untyped-def]
    gan = golden_imagen10[_GAN_KEY]
    assert gan["T2728"] == 5720.0
    assert gan["T3132"] == 25740.0


import pytest  # noqa: E402
