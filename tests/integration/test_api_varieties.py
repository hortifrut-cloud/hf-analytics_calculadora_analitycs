"""
Archivo: test_api_varieties.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para la gestión de variedades y sus curvas de 
producción (T4.2). Valida la creación, actualización de parámetros de 
productividad y eliminación de variedades asociadas a escenarios, 
garantizando la integridad de los datos de planificación.

Acciones Principales:
    - Validación de creación de variedades con curvas de 7 años.
    - Prevención de duplicidad de nombres de variedades por escenario.
    - Actualización masiva de parámetros de productividad/precio.
    - Verificación de eliminación y limpieza de relaciones.

Estructura Interna:
    - `test_create_variety`: Registro de nueva variedad.
    - `test_update_variety_params`: Edición de curvas de producción.
    - `test_delete_variety`: Remoción de variedad del escenario.

Ejecución:
    pytest tests/integration/test_api_varieties.py
"""

_V1_PARAMS = [
    {"plant_year": 1, "productividad": 2.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0},
    {"plant_year": 2, "productividad": 3.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0},
    {"plant_year": 3, "productividad": 4.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.9},
    {"plant_year": 4, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.8},
    {"plant_year": 5, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.7},
    {"plant_year": 6, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.6},
    {"plant_year": 7, "productividad": 5.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 0.6},
]


def _create_scenario(api_client, name="S"):
    r = api_client.post("/api/scenarios", json={"name": name})
    return r.json()["id"]


def test_create_variety(api_client):
    sid = _create_scenario(api_client, "SVar")
    r = api_client.post(
        f"/api/scenarios/{sid}/varieties",
        json={"name": "V1", "params": _V1_PARAMS},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "V1"
    assert "id" in body


def test_create_variety_duplicate_name(api_client):
    sid = _create_scenario(api_client, "SDup")
    api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    r2 = api_client.post(
        f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS}
    )
    assert r2.status_code == 409


def test_create_variety_scenario_not_found(api_client):
    r = api_client.post(
        "/api/scenarios/99999/varieties",
        json={"name": "V1", "params": _V1_PARAMS},
    )
    assert r.status_code == 404


def test_update_variety_params(api_client):
    sid = _create_scenario(api_client, "SUpd")
    r = api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    vid = r.json()["id"]

    new_params = [dict(p, productividad=10.0) for p in _V1_PARAMS]
    r2 = api_client.put(f"/api/varieties/{vid}/params", json={"params": new_params})
    assert r2.status_code == 200
    assert r2.json()["updated"] is True

    # Verificar que el escenario refleja los nuevos params
    state = api_client.get(f"/api/scenarios/{sid}").json()
    v = next(v for v in state["varieties"] if v["name"] == "V1")
    assert all(p["productividad"] == 10.0 for p in v["params"])


def test_delete_variety(api_client):
    sid = _create_scenario(api_client, "SDel")
    r = api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    vid = r.json()["id"]

    r2 = api_client.delete(f"/api/varieties/{vid}")
    assert r2.status_code == 200

    state = api_client.get(f"/api/scenarios/{sid}").json()
    assert not any(v["name"] == "V1" for v in state.get("varieties", []))
