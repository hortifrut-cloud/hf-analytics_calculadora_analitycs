"""
Archivo: test_api_scenarios.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para la gestión CRUD de escenarios (T4.2). Valida las 
operaciones básicas de creación, listado, lectura y eliminación de 
escenarios de planificación, asegurando la consistencia de los datos en 
el repositorio.

Acciones Principales:
    - Validación de creación de escenarios con nombres personalizados.
    - Verificación del listado global de escenarios.
    - Comprobación de recuperación de detalles por ID.
    - Validación del flujo de eliminación lógica y física.

Estructura Interna:
    - `test_create_scenario`: Prueba el registro de un nuevo escenario.
    - `test_list_scenarios`: Prueba la recuperación de la colección.
    - `test_delete_scenario`: Prueba la remoción y posterior inaccesibilidad.

Ejecución:
    pytest tests/integration/test_api_scenarios.py
"""


def test_create_scenario(api_client):
    r = api_client.post("/api/scenarios", json={"name": "Test Escenario"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Test Escenario"
    assert "id" in body


def test_list_scenarios(api_client):
    api_client.post("/api/scenarios", json={"name": "ListMe"})
    r = api_client.get("/api/scenarios")
    assert r.status_code == 200
    items = r.json()
    assert any(i["name"] == "ListMe" for i in items)


def test_get_scenario(api_client):
    r = api_client.post("/api/scenarios", json={"name": "GetMe"})
    sid = r.json()["id"]
    r2 = api_client.get(f"/api/scenarios/{sid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "GetMe"


def test_get_scenario_not_found(api_client):
    r = api_client.get("/api/scenarios/99999")
    assert r.status_code == 404


def test_delete_scenario(api_client):
    r = api_client.post("/api/scenarios", json={"name": "DeleteMe"})
    sid = r.json()["id"]
    r2 = api_client.delete(f"/api/scenarios/{sid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True
    # Verificar que ya no existe
    r3 = api_client.get(f"/api/scenarios/{sid}")
    assert r3.status_code == 404


def test_delete_scenario_not_found(api_client):
    r = api_client.delete("/api/scenarios/99999")
    assert r.status_code == 404
