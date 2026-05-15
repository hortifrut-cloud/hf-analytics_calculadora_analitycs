"""
Archivo: recambio.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo para el Bloque 2 (Recambio Varietal). Proyecta la producción 
y ganancia para renovaciones de variedades en terrenos de Hortifrut.

Acciones Principales:
    - Agregación estacional de hectáreas plantadas en el Bloque 2.
    - Aplicación de desfase fenológico.
    - Cálculo de producción y ganancia consolidada por variedad.

Estructura Interna:
    - `compute_recambio`: Función de cálculo para el bloque de recambio.

Ejemplo de Integración:
    from backend.logic.recambio import compute_recambio
    res = compute_recambio(scenario, calculos)
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import ScenarioState
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def compute_recambio(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Calcula los indicadores del bloque de Recambio Varietal.

    Args:
        scenario (ScenarioState): Estado del escenario.
        calculos (dict): Rendimientos por hectárea pre-calculados.

    Returns:
        dict: Subtotales estacionales por variedad.
    """
    result: dict[str, dict[str, dict[str, float]]] = {}

    for variety in scenario.varieties:
        ha_agg = aggregate_ha(
            scenario.new_project_cells, BloqueKind.RECAMBIO_VARIETAL, variety.name
        )
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
