"""Motor §3.6 — Bloque 1: Crecimiento Hortifrut (B1).

Sub-proyectos: CHAO, OLMOS (extensible).
Usa prod_hfi y gan_hfi de CalcVarRow.
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import ScenarioState
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def compute_crecimiento_hf(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, dict[str, float]]]:
    """Devuelve subtotales {variety_name: {'produccion': {season: val}, 'ganancia': {season: val}}}.

    Valores en miles de toneladas / miles de dólares.
    """
    result: dict[str, dict[str, dict[str, float]]] = {}

    for variety in scenario.varieties:
        ha_agg = aggregate_ha(scenario.new_project_cells, BloqueKind.CRECIMIENTO_HF, variety.name)
        lag = build_lag_matrix(ha_agg, max_plant_year=MAX_PLANT_YEAR)

        sub_prod: dict[str, float] = {s: 0.0 for s in SEASONS}
        sub_gan: dict[str, float] = {s: 0.0 for s in SEASONS}

        for n in range(1, MAX_PLANT_YEAR + 1):
            row = calculos.get((variety.name, n))
            if row is None:
                continue
            for season in SEASONS:
                ha = lag.loc[n, season]
                sub_prod[season] += ha * row.prod_hfi / 1000.0
                sub_gan[season] += ha * row.gan_hfi / 1000.0

        result[variety.name] = {"produccion": sub_prod, "ganancia": sub_gan}

    return result
