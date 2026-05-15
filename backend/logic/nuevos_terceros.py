"""
Archivo: nuevos_terceros.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo para el Bloque 3 (Nuevos Productores Terceros). Calcula la 
producción y la ganancia por royalties generada por plantaciones externas 
gestionadas bajo los modelos de negocio de Hortifrut.

Acciones Principales:
    - Agregación estacional de hectáreas plantadas por terceros.
    - Aplicación de desfase fenológico basado en la edad de la planta.
    - Cálculo de producción (KTM) y ganancia por royalties (MUSD) para Hortifrut.

Estructura Interna:
    - `compute_nuevos_terceros`: Función de cálculo para el bloque de terceros externos.

Ejemplo de Integración:
    from backend.logic.nuevos_terceros import compute_nuevos_terceros
    res = compute_nuevos_terceros(scenario, calculos)
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import ScenarioState
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def compute_nuevos_terceros(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Calcula la producción y ganancia FOB (royalties) para el bloque de 
    Nuevos Productores Terceros.

    Args:
        scenario (ScenarioState): Estado del escenario.
        calculos (dict): Diccionario de rendimientos y FOB por hectárea.

    Returns:
        dict: Subtotales de producción y ganancia por variedad y temporada.
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
            gan_total_hft = row.gan_venta_propia_hft + row.gan_venta_productor_hft
            for season in SEASONS:
                ha = lag.loc[n, season]
                sub_prod[season] += ha * row.prod_hft / 1000.0
                sub_gan[season] += ha * gan_total_hft / 1000.0

        result[variety.name] = {"produccion": sub_prod, "ganancia": sub_gan}

    return result
