"""
Archivo: terceros_totales.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo para el volumen y margen de productores terceros externos 
dentro del Bloque 3. Proyecta la fruta que no es propiedad de Hortifrut pero 
que forma parte del ecosistema del escenario.

Acciones Principales:
    - Agregación estacional de hectáreas de terceros.
    - Aplicación de desfase fenológico.
    - Cálculo de producción (KTM) y ganancia (MUSD) para el productor tercero.

Estructura Interna:
    - `compute_terceros_totales`: Calcula los subtotales de fruta y ganancia de terceros.

Ejemplo de Integración:
    from backend.logic.terceros_totales import compute_terceros_totales
    res = compute_terceros_totales(scenario, calculos)
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
    """
    Calcula los subtotales de producción y ganancia para los productores terceros.

    Args:
        scenario (ScenarioState): Estado del escenario.
        calculos (dict): Diccionario de rendimientos y FOB por hectárea.

    Returns:
        dict: Subtotales estacionales de terceros por variedad.
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
