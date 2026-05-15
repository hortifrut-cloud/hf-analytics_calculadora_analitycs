"""Tests integración — T4.2: CRUD escenarios."""


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
