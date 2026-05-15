"""
Archivo: test_invariants.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Suite de pruebas basadas en propiedades (*Property-based testing*) para el
motor de cálculos (T2.11). Utiliza la librería Hypothesis para generar
cientos de escenarios aleatorios y validar que el motor cumpla con los
invariantes matemáticos y de negocio definidos, asegurando la robustez
frente a casos de borde.

Sustentación Científica:
MacIver, D. R. (2015). Hypothesis: A new approach to property-based testing.

Acciones Principales:
    - Validación de no-negatividad en todos los resultados (producción/dinero).
    - Verificación del lag obligatorio en la primera temporada (T2627).
    - Comprobación del enmascaramiento de plantines según años de financiamiento.
    - Validación del determinismo del motor ante entradas idénticas.

Estructura Interna:
    - `variety_strategy`: Generador aleatorio de curvas de producción.
    - `scenario_strategy`: Generador de estados de escenario completos.
    - `test_crecimiento_non_negative`: Invariante de positividad.
    - `test_recompute_deterministic`: Invariante de consistencia.

Ejecución:
    pytest tests/property/test_invariants.py
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow,
    NewProjectCell,
    Rules,
    ScenarioState,
    Variety,
    VarietyParamRow,
)
from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.crecimiento_hf import compute_crecimiento_hf
from backend.logic.nuevos_terceros import compute_nuevos_terceros
from backend.logic.plantines import compute_plantines
from backend.logic.recambio import compute_recambio
from backend.logic.recompute import recompute
from backend.logic.terceros_totales import compute_terceros_totales

SEASONS = ALL_SEASONS

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_prod_st = st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False)
_pct_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_ha_st = st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False)
_fin_st = st.integers(min_value=1, max_value=7)
_cost_st = st.floats(min_value=0.0, max_value=20.0, allow_nan=False, allow_infinity=False)
_price_st = st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False)
_densidad_st = st.floats(min_value=100.0, max_value=20_000.0, allow_nan=False, allow_infinity=False)


@st.composite
def variety_strategy(draw):
    pcts = sorted(
        [draw(_pct_st) for _ in range(7)], reverse=True
    )  # decreasing pct makes agronomic sense but not required
    prods = [draw(_prod_st) for _ in range(7)]
    densidad = draw(_densidad_st)
    precio = draw(_price_st)
    params = [
        VarietyParamRow(
            plant_year=y,
            productividad=prods[y - 1],
            densidad=densidad,
            precio_estimado=precio,
            pct_recaudacion=pcts[y - 1],
        )
        for y in range(1, 8)
    ]
    return Variety(name="V1", params=params)


@st.composite
def scenario_strategy(draw, bloque: BloqueKind):
    variety = draw(variety_strategy())
    season = draw(st.sampled_from(SEASONS))
    ha = draw(_ha_st)
    fin = draw(_fin_st)
    cost = draw(_cost_st)
    rules = Rules(financiamiento_anios=fin, costo_plantines=cost)
    base_table = BaseTable(
        rows=[
            BaseTableRow(project_name="P", unit="tn", values={s: 0.0 for s in SEASONS}, total=0.0)
        ],
        variation={s: 0.0 for s in SEASONS},
    )
    cell = NewProjectCell(
        bloque=bloque, sub_proyecto="X", variety_name="V1", season=season, hectareas=ha
    )
    return ScenarioState(
        name="prop",
        base_table=base_table,
        varieties=[variety],
        rules=rules,
        new_project_cells=[cell],
    )


# ---------------------------------------------------------------------------
# Invariant 1: todos los valores de temporada son no-negativos
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.CRECIMIENTO_HF))
def test_crecimiento_non_negative(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_crecimiento_hf(scenario, calculos)
    for v in result:
        for s in SEASONS:
            assert result[v]["produccion"][s] >= 0.0
            assert result[v]["ganancia"][s] >= 0.0


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.RECAMBIO_VARIETAL))
def test_recambio_non_negative(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_recambio(scenario, calculos)
    for v in result:
        for s in SEASONS:
            assert result[v]["produccion"][s] >= 0.0
            assert result[v]["ganancia"][s] >= 0.0


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.NUEVOS_TERCEROS))
def test_nuevos_terceros_non_negative(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_nuevos_terceros(scenario, calculos)
    for v in result:
        for s in SEASONS:
            assert result[v]["produccion"][s] >= 0.0
            assert result[v]["ganancia"][s] >= 0.0


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.NUEVOS_TERCEROS))
def test_plantines_non_negative(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_plantines(scenario, calculos)
    for v in result:
        for s in SEASONS:
            assert result[v][s] >= 0.0


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.NUEVOS_TERCEROS))
def test_terceros_totales_non_negative(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_terceros_totales(scenario, calculos)
    for v in result:
        for s in SEASONS:
            assert result[v]["produccion"][s] >= 0.0
            assert result[v]["ganancia"][s] >= 0.0


# ---------------------------------------------------------------------------
# Invariant 2: T2627 siempre 0 (lag de al menos 1 período)
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.CRECIMIENTO_HF))
def test_first_season_always_zero_crecimiento(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_crecimiento_hf(scenario, calculos)
    for v in result:
        assert result[v]["produccion"]["T2627"] == 0.0
        assert result[v]["ganancia"]["T2627"] == 0.0


@settings(max_examples=200)
@given(scenario_strategy(BloqueKind.NUEVOS_TERCEROS))
def test_first_season_always_zero_plantines(scenario):
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_plantines(scenario, calculos)
    for v in result:
        assert result[v]["T2627"] == 0.0


# ---------------------------------------------------------------------------
# Invariant 3: plantines=0 si n > financiamiento_anios para siembra en T2627
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    variety_strategy(),
    st.integers(min_value=1, max_value=6),
    st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
)
def test_plantines_mask_respected(variety, fin, ha):
    rules = Rules(financiamiento_anios=fin, costo_plantines=3.5)
    base_table = BaseTable(
        rows=[
            BaseTableRow(project_name="P", unit="tn", values={s: 0.0 for s in SEASONS}, total=0.0)
        ],
        variation={s: 0.0 for s in SEASONS},
    )
    # Siembra solo en T2627 → año n contribuye a seasons[n] (índice n)
    cell = NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS,
        sub_proyecto="X",
        variety_name="V1",
        season="T2627",
        hectareas=ha,
    )
    scenario = ScenarioState(
        name="p", base_table=base_table, varieties=[variety], rules=rules, new_project_cells=[cell]
    )
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)
    result = compute_plantines(scenario, calculos)
    # Todos los años n > fin deben ser 0 en la temporada correspondiente
    for n in range(fin + 1, 8):
        if n < len(SEASONS):
            assert result["V1"][SEASONS[n]] == 0.0, f"plantines n={n} debe ser 0 con fin={fin}"


# ---------------------------------------------------------------------------
# Invariant 4: recompute es determinístico
# ---------------------------------------------------------------------------


@settings(max_examples=50)
@given(scenario_strategy(BloqueKind.CRECIMIENTO_HF))
def test_recompute_deterministic(scenario):
    r1 = recompute(scenario)
    r2 = recompute(scenario)
    for key in (
        "crecimiento",
        "recambio",
        "nuevos_terceros",
        "plantines",
        "terceros_totales",
        "totales",
    ):
        assert r1[key] == r2[key]
