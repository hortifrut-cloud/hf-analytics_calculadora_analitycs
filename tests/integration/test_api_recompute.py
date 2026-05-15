"""
Archivo: test_api_recompute.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para el motor de cálculos a través del endpoint 
`recompute` (T4.3). Valida que el backend procese correctamente los datos 
de un escenario completo y devuelva los resultados esperados (fruta, 
ganancia, plantines) coincidiendo con los "Golden Masters" definidos en 
UI.png.

Acciones Principales:
    - Validación del flujo completo de cálculo desde la API.
    - Aserción de valores de fruta y ganancia para el escenario canónico.
    - Verificación del manejo de errores para escenarios inexistentes.

Estructura Interna:
    - `ui_png_scenario`: Fixture que prepara un escenario idéntico a UI.png.
    - `test_recompute_hf_fruta_t2728`: Valida el bloque de fruta HF.
    - `test_recompute_hf_ganancia_t2728`: Valida el bloque de ganancia HF.

Ejecución:
    pytest tests/integration/test_api_recompute.py
"""

import pytest

_V1_PARAMS = [
    {"plant_year": 1, "productividad": 2.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0},
    {"plant_year": 2, "productividad": 3.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0},
    {"plant_year": 3, "productividad": 4.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.9},
    {"plant_year": 4, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.8},
    {"plant_year": 5, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.7},
    {"plant_year": 6, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.6},
    {"plant_year": 7, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.6},
]

_CELLS = [
    {"bloque": "crecimiento_hf", "sub_proyecto": "CHAO", "variety_name": "V1", "season": "T2627", "hectareas": 250.0},
    {"bloque": "crecimiento_hf", "sub_proyecto": "OLMOS", "variety_name": "V1", "season": "T2728", "hectareas": 200.0},
    {"bloque": "recambio_varietal", "sub_proyecto": "OLMOS", "variety_name": "V1", "season": "T2627", "hectareas": 50.0},
    {"bloque": "nuevos_terceros", "sub_proyecto": "Talsa", "variety_name": "V1", "season": "T2627", "hectareas": 100.0},
    {"bloque": "nuevos_terceros", "sub_proyecto": "Talsa", "variety_name": "V1", "season": "T2728", "hectareas": 100.0},
    {"bloque": "nuevos_terceros", "sub_proyecto": "Diamond Bridge", "variety_name": "V1", "season": "T2627", "hectareas": 25.0},
]


@pytest.fixture
def ui_png_scenario(api_client):
    """Escenario UI.png completo vía API."""
    sid = api_client.post("/api/scenarios", json={"name": "UI PNG"}).json()["id"]
    api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    for cell in _CELLS:
        api_client.put(f"/api/scenarios/{sid}/new-projects", json=cell)
    return sid


def test_recompute_returns_200(api_client, ui_png_scenario):
    r = api_client.post(f"/api/scenarios/{ui_png_scenario}/recompute")
    assert r.status_code == 200


def test_recompute_hf_fruta_t2728(api_client, ui_png_scenario):
    r = api_client.post(f"/api/scenarios/{ui_png_scenario}/recompute")
    totales = r.json()["totales"]
    hf_fruta_t2728 = totales["hf_fruta"]["T2728"]
    # B1=3250 + B2=650 + B3=1625
    assert abs(hf_fruta_t2728 - 5525.0) <= 1.0


def test_recompute_hf_ganancia_t2728(api_client, ui_png_scenario):
    r = api_client.post(f"/api/scenarios/{ui_png_scenario}/recompute")
    totales = r.json()["totales"]
    hf_gan = totales["hf_ganancia"]["T2728"]
    # 13000 + 2600 + 780 + 568.75 plantines
    assert abs(hf_gan - 16948.75) <= 1.0


def test_recompute_terceros_fruta_t2930(api_client, ui_png_scenario):
    r = api_client.post(f"/api/scenarios/{ui_png_scenario}/recompute")
    totales = r.json()["totales"]
    terceros_fruta = totales["terceros_fruta"]["T2930"]
    assert abs(terceros_fruta - 325.0) <= 1.0


def test_recompute_scenario_not_found(api_client):
    r = api_client.post("/api/scenarios/99999/recompute")
    assert r.status_code == 404
