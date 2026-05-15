"""Motor §3.9 — Sub-bloque Terceros para Totales.

Usa solo hectáreas de B3; campos prod_terceros y (gan_venta_hf_terceros + gan_venta_propia_terceros).
Nota: para años con pct_recaudacion=1.0 (ej. año 1 y 2 de V1), prod_terceros=0 → producción=0.
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import ScenarioState
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def compute_terceros_totales(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, dict[str, float]]]:
    """Devuelve subtotales {variety_name: {'produccion': ..., 'ganancia': ...}}.

    Producción = prod_terceros; Ganancia = gan_venta_hf_terceros + gan_venta_propia_terceros.
    """
    result: dict[str, dict[str, dict[str, float]]] = {}

    for variety in scenario.varieties:
        ha_agg = aggregate_ha(scenario.new_project_cells, BloqueKind.NUEVOS_TERCEROS, variety.name)
        lag = build_lag_matrix(ha_agg, max_plant_year=MAX_PLANT_YEAR)

        sub_prod: dict[str, float] = {s: 0.0 for s in SEASONS}
        sub_gan: dict[str, float] = {s: 0.0 for s in SEASONS}

        for n in range(1, MAX_PLANT_YEAR + 1):
            row = calculos.get((variety.name, n))
            if row is None:
                continue
            gan_total = row.gan_venta_hf_terceros + row.gan_venta_propia_terceros
            for season in SEASONS:
                ha = lag.loc[n, season]
                sub_prod[season] += ha * row.prod_terceros / 1000.0
                sub_gan[season] += ha * gan_total / 1000.0

        result[variety.name] = {"produccion": sub_prod, "ganancia": sub_gan}

    return result
