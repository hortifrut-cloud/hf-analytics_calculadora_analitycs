"""Orquestador §3 — recompute(scenario) -> DerivedState.

Orden topológico:
  calculos_variedades
  → crecimiento_hf, recambio, nuevos_terceros  (independientes)
  → plantines
  → terceros_totales
  → totales
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
    """Ejecuta todo el motor y devuelve un dict con todos los sub-resultados.

    Retorna un dict plano (no DerivedState aún — ese modelo se actualiza en Fase 3).
    Keys: 'calculos', 'crecimiento', 'recambio', 'nuevos_terceros',
          'plantines', 'terceros_totales', 'totales'.
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
