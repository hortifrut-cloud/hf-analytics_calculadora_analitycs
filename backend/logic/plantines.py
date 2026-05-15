"""
Archivo: plantines.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo para la ganancia por venta de plantines en el Bloque 3 
(Nuevos Terceros). Modela el ingreso por la venta y financiamiento de material 
genético a productores externos.

Acciones Principales:
    - Cálculo de la cuota de amortización por hectárea según financiamiento.
    - Aplicación de máscara temporal para limitar el cobro a los años de financiamiento.
    - Proyección estacional de ingresos por plantines (MUSD).

Estructura Interna:
    - `cuota_amortizacion`: Calcula el pago periódico del capital.
    - `compute_plantines`: Orquestador de cálculos para el bloque de plantines.

Ejemplo de Integración:
    from backend.logic.plantines import compute_plantines
    res = compute_plantines(scenario, calculos)
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import Rules, ScenarioState, Variety
from backend.logic.calculos_variedades import CalcVarRow
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

MAX_PLANT_YEAR = 7
SEASONS = ALL_SEASONS


def cuota_amortizacion(capital: float, i: float, n: int) -> float:
    """
    Calcula la cuota periódica de amortización de un préstamo.

    Args:
        capital (float): Monto total a financiar.
        i (float): Tasa de interés periódica.
        n (int): Número de periodos de pago.

    Returns:
        float: Valor de la cuota constante.
    """
    if i == 0.0:
        return capital / n
    return capital * i / (1.0 - (1.0 + i) ** (-n))


def compute_plantines(
    scenario: ScenarioState,
    calculos: dict[tuple[str, int], CalcVarRow],
) -> dict[str, dict[str, float]]:
    """
    Calcula los subtotales de ingresos por plantines para el bloque de 
    Nuevos Productores Terceros.

    Args:
        scenario (ScenarioState): Estado del escenario.
        calculos (dict): Diccionario de parámetros técnicos.

    Returns:
        dict: Mapeo de variedad a ingresos estacionales por plantines.
    """
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
