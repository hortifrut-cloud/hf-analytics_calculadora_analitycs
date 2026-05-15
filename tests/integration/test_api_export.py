"""Tests integración — T4.4: export XLSX."""

_V1_PARAMS = [
    {"plant_year": i, "productividad": 2.0, "densidad": 6500, "precio_estimado": 4.0, "pct_recaudacion": 1.0}
    for i in range(1, 8)
]


def _make_scenario(api_client):
    sid = api_client.post("/api/scenarios", json={"name": "Export Test"}).json()["id"]
    api_client.post(f"/api/scenarios/{sid}/varieties", json={"name": "V1", "params": _V1_PARAMS})
    api_client.put(
        f"/api/scenarios/{sid}/new-projects",
        json={
            "bloque": "crecimiento_hf",
            "sub_proyecto": "CHAO",
            "variety_name": "V1",
            "season": "T2627",
            "hectareas": 250.0,
        },
    )
    return sid


def test_export_returns_xlsx_content_type(api_client):
    sid = _make_scenario(api_client)
    r = api_client.get(f"/api/scenarios/{sid}/export.xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]


def test_export_file_not_empty(api_client):
    sid = _make_scenario(api_client)
    r = api_client.get(f"/api/scenarios/{sid}/export.xlsx")
    assert len(r.content) > 1000  # XLSX mínimo tiene magic bytes + hojas


def test_export_xlsx_has_5_sheets(api_client):
    import io
    import openpyxl

    sid = _make_scenario(api_client)
    r = api_client.get(f"/api/scenarios/{sid}/export.xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    assert len(wb.sheetnames) == 5


def test_export_scenario_not_found(api_client):
    r = api_client.get("/api/scenarios/99999/export.xlsx")
    assert r.status_code == 404
