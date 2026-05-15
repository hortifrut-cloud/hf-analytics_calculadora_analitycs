"""
Archivo: crecimiento_hf.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo para el Bloque 1 (Crecimiento Hortifrut). Proyecta la 
producción y ganancia FOB para las nuevas plantaciones en terrenos propios 
de Hortifrut (ej. Chao, Olmos).

Acciones Principales:
    - Agregación estacional de hectáreas plantadas en el Bloque 1.
    - Aplicación de la matriz de desfase para determinar la edad de la planta.
    - Cálculo de producción (KTM) y ganancia (MUSD) por variedad.

Estructura Interna:
    - `compute_crecimiento_hf`: Calcula los subtotales estacionales para el bloque.

Ejemplo de Integración:
    from backend.logic.crecimiento_hf import compute_crecimiento_hf
    subtotals = compute_crecimiento_hf(scenario, calculos_dict)
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
    """
    Calcula los subtotales de producción y ganancia para el bloque de 
    Crecimiento Hortifrut.

    Args:
        scenario (ScenarioState): Estado del escenario con las celdas de proyectos.
        calculos (dict): Diccionario de rendimientos por variedad y año.

    Returns:
        dict: Estructura {variedad: {'produccion': {temporada: valor}, 'ganancia': {...}}}.
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
