"""
Archivo: recompute.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Orquestador principal del motor de cálculo. Coordina la ejecución secuencial
de todos los módulos de lógica siguiendo un orden topológico estricto para
garantizar la integridad de los resultados derivados.

Orden de Ejecución:
    1. calculos_variedades (Base técnica)
    2. crecimiento_hf, recambio, nuevos_terceros (Capas de producción)
    3. plantines (Costo de establecimiento)
    4. terceros_totales (Segregación de fruta)
    5. totales (Consolidación final)

Estructura Interna:
    - `recompute`: Función principal que transforma un ScenarioState en un diccionario de resultados.

Ejemplo de Integración:
    from backend.logic.recompute import recompute
    results = recompute(scenario_state)
"""

from typing import Any

from backend.domain.inputs import ScenarioState
from backend.logic.calculos_variedades import compute_calculos_variedades
from backend.logic.crecimiento_hf import compute_crecimiento_hf
from backend.logic.nuevos_terceros import compute_nuevos_terceros
from backend.logic.plantines import compute_plantines
from backend.logic.recambio import compute_recambio
from backend.logic.terceros_totales import compute_terceros_totales
from backend.logic.totales import compute_totales


def recompute(scenario: ScenarioState) -> dict[str, Any]:
    """
    Ejecuta el motor analítico completo y consolida todos los sub-resultados.

    Args:
        scenario (ScenarioState): Estado inmutable del escenario a procesar.

    Returns:
        dict[str, Any]: Diccionario plano con las llaves 'calculos', 'crecimiento', 
        'recambio', 'nuevos_terceros', 'plantines', 'terceros_totales' y 'totales'.
    """
    calculos = compute_calculos_variedades(list(scenario.varieties), scenario.rules)

    crecimiento = compute_crecimiento_hf(scenario, calculos)
    recambio = compute_recambio(scenario, calculos)
    nuevos_t = compute_nuevos_terceros(scenario, calculos)
    plant = compute_plantines(scenario, calculos)
    terceros = compute_terceros_totales(scenario, calculos)
    totales = compute_totales(crecimiento, recambio, nuevos_t, plant, terceros)

    return {
        "calculos": calculos,
        "crecimiento": crecimiento,
        "recambio": recambio,
        "nuevos_terceros": nuevos_t,
        "plantines": plant,
        "terceros_totales": terceros,
        "totales": totales,
    }
