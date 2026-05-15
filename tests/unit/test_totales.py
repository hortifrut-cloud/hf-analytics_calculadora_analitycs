"""
Archivo: test_totales.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para la lógica de agregación final de resultados (T2.9).
Valida la consolidación de los tres bloques productivos y el
financiamiento de plantines en los indicadores globales del escenario,
asegurando que se mantenga la separación estricta entre los resultados de
Hortifrut y los de terceros.

Acciones Principales:
    - Validación de la suma de producción de todos los bloques para HF.
    - Verificación de la consolidación de ganancias (incluyendo plantines).
    - Validación de la independencia de los indicadores de terceros.
    - Comprobación de integridad ante diccionarios de resultados vacíos.

Estructura Interna:
    - `test_hf_fruta_suma_b1_b2_b3`: Verifica la producción total de fruta.
    - `test_hf_ganancia_incluye_plantines`: Verifica el margen total de HF.
    - `test_terceros_separados`: Verifica que terceros no afecten métricas HF.

Ejecución:
    pytest tests/unit/test_totales.py
"""

import pytest

from backend.logic.totales import compute_totales

SEASONS = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]


def _make_subtotales(prod_vals: dict, gan_vals: dict) -> dict:
    prod = {s: prod_vals.get(s, 0.0) for s in SEASONS}
    gan = {s: gan_vals.get(s, 0.0) for s in SEASONS}
    return {"produccion": prod, "ganancia": gan}


def test_hf_fruta_suma_b1_b2_b3():
    """HF fruta = B1 + B2 + B3 producción."""
    crecimiento = {"V1": _make_subtotales({"T2728": 3250.0}, {"T2728": 13000.0})}
    recambio = {"V1": _make_subtotales({"T2728": 650.0}, {"T2728": 2600.0})}
    nuevos = {"V1": _make_subtotales({"T2728": 1625.0}, {"T2728": 780.0})}
    plantines = {"V1": {s: 0.0 for s in SEASONS}}
    plantines["V1"]["T2728"] = 568.75
    terceros = {"V1": _make_subtotales({}, {"T2728": 5720.0})}

    result = compute_totales(crecimiento, recambio, nuevos, plantines, terceros)
    assert result["hf_fruta"]["T2728"] == pytest.approx(3250.0 + 650.0 + 1625.0, abs=1)


def test_hf_ganancia_incluye_plantines():
    """HF ganancia incluye plantines."""
    crecimiento = {"V1": _make_subtotales({}, {"T2728": 13000.0})}
    recambio = {"V1": _make_subtotales({}, {"T2728": 2600.0})}
    nuevos = {"V1": _make_subtotales({}, {"T2728": 780.0})}
    plantines = {"V1": {s: 0.0 for s in SEASONS}}
    plantines["V1"]["T2728"] = 568.75
    terceros = {"V1": _make_subtotales({}, {})}

    result = compute_totales(crecimiento, recambio, nuevos, plantines, terceros)
    assert result["hf_ganancia"]["T2728"] == pytest.approx(13000.0 + 2600.0 + 780.0 + 568.75, abs=1)


def test_terceros_separados():
    """Terceros no se mezcla con HF."""
    empty = {"V1": _make_subtotales({}, {})}
    plantines = {"V1": {s: 0.0 for s in SEASONS}}
    terceros = {"V1": _make_subtotales({"T2930": 325.0}, {"T2728": 5720.0})}

    result = compute_totales(empty, empty, empty, plantines, terceros)
    assert result["terceros_fruta"]["T2930"] == pytest.approx(325.0, abs=1)
    assert result["terceros_ganancia"]["T2728"] == pytest.approx(5720.0, abs=1)
    assert result["hf_fruta"]["T2930"] == 0.0


def test_empty_returns_zeros():
    empty = {}
    result = compute_totales(empty, empty, empty, empty, empty)
    for s in SEASONS:
        assert result["hf_fruta"][s] == 0.0
        assert result["hf_ganancia"][s] == 0.0
        assert result["terceros_fruta"][s] == 0.0
        assert result["terceros_ganancia"][s] == 0.0
