"""Motor §3.8.2 — Ganancia Plantines (B3 exclusivo).

Fórmula:  GP(n, t) = ha(t-n) × Densidad(n) × Costo_Plantines / Financiamiento / 1000
Máscara:  GP(n, t) = 0  si  n > Financiamiento_anios

Hook futuro: cuota_amortizacion() para interés > 0 (no usada aún).
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import Rules, ScenarioState, Variety
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def cuota_amortizacion(capital: float, i: float, n: int) -> float:
    """Cuota fija de amortización.  Cuota = Capital × i / (1 − (1+i)^(−n))."""
    if i == 0.0:
        return capital / n
    return capital * i / (1.0 - (1.0 + i) ** (-n))


def compute_plantines(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, float]]:
    """Devuelve subtotales plantines {variety_name: {season: valor_miles}}."""
    rules: Rules = scenario.rules
    fin = rules.financiamiento_anios
    result: dict[str, dict[str, float]] = {}

    for variety in scenario.varieties:
        ha_agg = aggregate_ha(scenario.new_project_cells, BloqueKind.NUEVOS_TERCEROS, variety.name)
        lag = build_lag_matrix(ha_agg, max_plant_year=MAX_PLANT_YEAR)

        sub_plan: dict[str, float] = {s: 0.0 for s in SEASONS}

        for n in range(1, MAX_PLANT_YEAR + 1):
            if n > fin:
                continue  # máscara de truncamiento
            row = calculos.get((variety.name, n))
            if row is None:
                continue
            # Densidad proviene del param del año n de la variedad
            densidad = next(p.densidad for p in variety.params if p.plant_year == n)
            gp_por_ha = densidad * rules.costo_plantines / fin  # FOB/ha
            for season in SEASONS:
                ha = lag.loc[n, season]
                sub_plan[season] += ha * gp_por_ha / 1000.0

        result[variety.name] = sub_plan

    return result
