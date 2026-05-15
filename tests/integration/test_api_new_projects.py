"""
Archivo: test_api_new_projects.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para el endpoint de gestión de hectáreas en nuevos 
proyectos (T4.2). Valida la lógica de "upsert" (creación o actualización) 
de celdas de planificación, asegurando que los cambios se persistan 
correctamente en la base de datos y que las validaciones de negocio se 
apliquen.

Acciones Principales:
    - Validación de creación de nuevas celdas de hectáreas.
    - Validación de actualización de valores existentes.
    - Control de errores para variedades o escenarios inexistentes.

Estructura Interna:
    - `test_upsert_cell_create`: Prueba la inserción inicial.
    - `test_upsert_cell_update`: Prueba la modificación de valores.
    - `test_upsert_cell_variety_not_found`: Valida integridad referencial.

Ejecución:
    pytest tests/integration/test_api_new_projects.py
"""

_V1_PARAMS = [
    {"plant_year": i, "productividad": 2.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0}
    for i in range(1, 8)
]


def _setup(api_client):
    sid = api_client.post("/api/scenarios", json={"name": "NP"}).json()["id"]
    api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    return sid


def test_upsert_cell_create(api_client):
    sid = _setup(api_client)
    r = api_client.put(
        f"/api/scenarios/{sid}/new-projects",
        json={
            "bloque": "crecimiento_hf",
            "sub_proyecto": "CHAO",
            "variety_name": "V1",
            "season": "T2627",
            "hectareas": 250.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["hectareas"] == 250.0


def test_upsert_cell_update(api_client):
    sid = _setup(api_client)
    payload = {
        "bloque": "crecimiento_hf",
        "sub_proyecto": "OLMOS",
        "variety_name": "V1",
        "season": "T2728",
        "hectareas": 100.0,
    }
    api_client.put(f"/api/scenarios/{sid}/new-projects", json=payload)
    # Actualizar a 200
    payload["hectareas"] = 200.0
    r2 = api_client.put(f"/api/scenarios/{sid}/new-projects", json=payload)
    assert r2.status_code == 200
    assert r2.json()["hectareas"] == 200.0


def test_upsert_cell_variety_not_found(api_client):
    sid = _setup(api_client)
    r = api_client.put(
        f"/api/scenarios/{sid}/new-projects",
        json={
            "bloque": "crecimiento_hf",
            "sub_proyecto": "CHAO",
            "variety_name": "INEXISTENTE",
            "season": "T2627",
            "hectareas": 100.0,
        },
    )
    assert r.status_code == 404


def test_upsert_cell_scenario_not_found(api_client):
    r = api_client.put(
        "/api/scenarios/99999/new-projects",
        json={
            "bloque": "crecimiento_hf",
            "sub_proyecto": "CHAO",
            "variety_name": "V1",
            "season": "T2627",
            "hectareas": 100.0,
        },
    )
    assert r.status_code == 404
