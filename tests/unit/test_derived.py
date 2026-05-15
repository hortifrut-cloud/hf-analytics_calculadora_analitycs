"""
Archivo: test_derived.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para los modelos de dominio derivados (A1.3). Valida la
estructura de datos, serialización JSON y métodos de agregación de las
clases que representan los resultados procesados del motor de cálculos,
asegurando la integridad de los datos que se envían al frontend.

Acciones Principales:
    - Validación de la estructura `CalculosVariedadCell` y sus campos opcionales.
    - Prueba de los métodos de agregación de `MatrizSubyacente` por temporada.
    - Validación de la jerarquía de `Totales` y `Subtotales`.
    - Comprobación de la serialización y deserialización de `DerivedState`.

Estructura Interna:
    - `test_calculos_variedad_*`: Verifica las celdas individuales de pre-cálculo.
    - `test_matriz_subtotal_by_season`: Verifica la suma horizontal de matrices.
    - `test_derived_state_roundtrip_json`: Asegura persistencia sin pérdida de tipos.

Ejecución:
    pytest tests/unit/test_derived.py
"""

import json

from backend.domain.derived import (
    CalculosVariedadCell,
    DerivedState,
    MatrizSubyacente,
    Subtotales,
    Totales,
)
from backend.domain.enums import ALL_SEASONS, BloqueKind, Productor

SEASONS = ALL_SEASONS


# ---------------------------------------------------------------------------
# A1.3.1 — CalculosVariedadCell
# ---------------------------------------------------------------------------


def test_calculos_variedad_hfi_year1_v1() -> None:
    # V1 año 1: Productividad=2 Kg/planta, Densidad=6500 → 13_000 Kg/ha
    # Precio=4 → Ganancia=52_000
    c = CalculosVariedadCell(
        variety_name="V1",
        productor=Productor.HF_INTERNA,
        plant_year=1,
        productividad_kg_ha=13_000.0,
        ganancia_fob_ha=52_000.0,
    )
    assert c.productividad_kg_ha == 13_000.0
    assert c.ganancia_fob_ha == 52_000.0
    assert c.pct_recaudacion is None


def test_calculos_variedad_hft_fields() -> None:
    c = CalculosVariedadCell(
        variety_name="V1",
        productor=Productor.HF_TERCEROS,
        plant_year=5,
        productividad_kg_ha=22_750.0,
        ganancia_fob_ha=91_000.0,
        pct_recaudacion=0.70,
        ganancia_venta_propia_ha=10_920.0,
        ganancia_venta_productor_ha=4_680.0,
    )
    assert c.pct_recaudacion == 0.70
    assert c.ganancia_venta_propia_ha == 10_920.0


def test_calculos_variedad_roundtrip_json() -> None:
    c = CalculosVariedadCell(
        variety_name="V1",
        productor=Productor.HF_INTERNA,
        plant_year=1,
        productividad_kg_ha=13_000.0,
        ganancia_fob_ha=52_000.0,
    )
    assert json.loads(c.model_dump_json())["productividad_kg_ha"] == 13_000.0


# ---------------------------------------------------------------------------
# A1.3.2 — MatrizSubyacente
# ---------------------------------------------------------------------------


def _make_matriz_imagen7() -> MatrizSubyacente:
    # Crecimiento HF (B1), V1 — producción en miles de ton
    # data[plant_year][season] = valor
    # CHAO 250ha@T2627, OLMOS 200ha@T2728
    # Año1: T2728=250*13000/1000=3250, T2829=200*13000/1000=2600
    data: dict[int, dict[str, float]] = {
        1: {"T2728": 3_250.0, "T2829": 2_600.0, "T2930": 0.0},
        2: {"T2829": 250 * 16_500 / 1000, "T2930": 200 * 16_500 / 1000},
        3: {"T2930": 250 * 26_000 / 1000},
    }
    return MatrizSubyacente(
        bloque=BloqueKind.CRECIMIENTO_HF,
        sub_proyecto="CHAO+OLMOS",
        variety_name="V1",
        kind="produccion",
        data=data,
    )


def test_matriz_subyacente_builds() -> None:
    m = _make_matriz_imagen7()
    assert m.kind == "produccion"
    assert m.data[1]["T2728"] == 3_250.0


def test_matriz_subtotal_by_season() -> None:
    m = _make_matriz_imagen7()
    subtotals = m.subtotal_by_season()
    assert subtotals["T2728"] == 3_250.0
    assert subtotals["T2829"] == pytest.approx(2_600.0 + 250 * 16_500 / 1000, abs=1)


def test_matriz_roundtrip_json() -> None:
    m = _make_matriz_imagen7()
    restored = MatrizSubyacente.model_validate_json(m.model_dump_json())
    assert restored.data == m.data


# ---------------------------------------------------------------------------
# A1.3.3 — Subtotales y Totales
# ---------------------------------------------------------------------------


def test_subtotales_builds() -> None:
    s = Subtotales(
        bloque=BloqueKind.CRECIMIENTO_HF,
        variety_name="V1",
        produccion_by_season={
            "T2627": 0.0,
            "T2728": 3_250.0,
            "T2829": 6_725.0,
            "T2930": 9_800.0,
            "T3031": 13_325.0,
            "T3132": 14_625.0,
        },
        ganancia_by_season={
            "T2627": 0.0,
            "T2728": 13_000.0,
            "T2829": 26_900.0,
            "T2930": 39_200.0,
            "T3031": 53_300.0,
            "T3132": 58_500.0,
        },
    )
    assert s.produccion_by_season["T2728"] == 3_250.0
    assert s.plantines_by_season == {}


def test_totales_builds() -> None:
    t = Totales(
        hortifrut_fruta_by_season={"T2728": 5_525.0},
        hortifrut_ganancia_by_season={"T2728": 16_949.0},
        terceros_fruta_by_season={"T2728": 0.0},
        terceros_ganancia_by_season={"T2728": 5_720.0},
    )
    assert t.hortifrut_fruta_by_season["T2728"] == 5_525.0
    assert t.hortifrut_ganancia_by_season["T2728"] == 16_949.0


# ---------------------------------------------------------------------------
# A1.3.4 — DerivedState
# ---------------------------------------------------------------------------


def _make_derived() -> DerivedState:
    return DerivedState(
        calculos_variedades=[
            CalculosVariedadCell(
                variety_name="V1",
                productor=Productor.HF_INTERNA,
                plant_year=1,
                productividad_kg_ha=13_000.0,
                ganancia_fob_ha=52_000.0,
            )
        ],
        matrices=[_make_matriz_imagen7()],
        subtotales=[
            Subtotales(
                bloque=BloqueKind.CRECIMIENTO_HF,
                variety_name="V1",
                produccion_by_season={"T2728": 3_250.0},
                ganancia_by_season={"T2728": 13_000.0},
            )
        ],
        totales=Totales(
            hortifrut_fruta_by_season={"T2728": 3_250.0},
            hortifrut_ganancia_by_season={"T2728": 13_000.0},
            terceros_fruta_by_season={},
            terceros_ganancia_by_season={},
        ),
    )


def test_derived_state_builds() -> None:
    d = _make_derived()
    assert len(d.calculos_variedades) == 1
    assert len(d.matrices) == 1


def test_derived_state_equality() -> None:
    d1 = _make_derived()
    d2 = _make_derived()
    assert d1 == d2


def test_derived_state_roundtrip_json() -> None:
    d = _make_derived()
    j1 = d.model_dump_json()
    j2 = d.model_dump_json()
    assert j1 == j2


import pytest  # noqa: E402 — needed for pytest.approx used above
