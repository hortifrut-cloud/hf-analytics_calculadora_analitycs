"""
Archivo: totales.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Módulo de consolidación final del escenario. Suma los resultados de todos los 
bloques (Crecimiento, Recambio, Terceros y Plantines) para generar los 
indicadores agregados de producción y ganancia, segregados por la naturaleza 
de la propiedad (Hortifrut vs Terceros).

Acciones Principales:
    - Agregación de producción KTM para Hortifrut (Propios + Royalties).
    - Agregación de ganancia MUSD para Hortifrut (Directa + Royalties + Plantines).
    - Consolidación de fruta y margen de terceros externos.

Estructura Interna:
    - `compute_totales`: Función de agregación final que recibe los outputs de todos los bloques.

Ejemplo de Integración:
    from backend.logic.totales import compute_totales
    final_results = compute_totales(crecimiento, recambio, nuevos, plantines, terceros)
"""

from backend.domain.enums import ALL_SEASONS

SEASONS = ALL_SEASONS


def compute_totales(
    crecimiento: dict[str, dict[str, dict[str, float]]],
    recambio: dict[str, dict[str, dict[str, float]]],
    nuevos_terceros: dict[str, dict[str, dict[str, float]]],
    plantines: dict[str, dict[str, float]],
    terceros_totales: dict[str, dict[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    """
    Consolida todos los indicadores técnicos y económicos por temporada.

    Args:
        crecimiento (dict): Resultados del bloque B1.
        recambio (dict): Resultados del bloque B2.
        nuevos_terceros (dict): Resultados del bloque B3 (Royalties).
        plantines (dict): Resultados de venta de plantines.
        terceros_totales (dict): Resultados de fruta de terceros.

    Returns:
        dict: Totales consolidados {'hf_fruta', 'hf_ganancia', 'terceros_fruta', 'terceros_ganancia'}.
    """
    hf_fruta: dict[str, float] = {s: 0.0 for s in SEASONS}
    hf_ganancia: dict[str, float] = {s: 0.0 for s in SEASONS}
    terceros_fruta: dict[str, float] = {s: 0.0 for s in SEASONS}
    terceros_ganancia: dict[str, float] = {s: 0.0 for s in SEASONS}

    all_varieties = (
        set(crecimiento)
        | set(recambio)
        | set(nuevos_terceros)
        | set(plantines)
        | set(terceros_totales)
    )

    for variety in all_varieties:
        for s in SEASONS:
            hf_fruta[s] += (
                crecimiento.get(variety, {}).get("produccion", {}).get(s, 0.0)
                + recambio.get(variety, {}).get("produccion", {}).get(s, 0.0)
                + nuevos_terceros.get(variety, {}).get("produccion", {}).get(s, 0.0)
            )
            hf_ganancia[s] += (
                crecimiento.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + recambio.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + nuevos_terceros.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + plantines.get(variety, {}).get(s, 0.0)
            )
            terceros_fruta[s] += terceros_totales.get(variety, {}).get("produccion", {}).get(s, 0.0)
            terceros_ganancia[s] += (
                terceros_totales.get(variety, {}).get("ganancia", {}).get(s, 0.0)
            )

    return {
        "hf_fruta": hf_fruta,
        "hf_ganancia": hf_ganancia,
        "terceros_fruta": terceros_fruta,
        "terceros_ganancia": terceros_ganancia,
    }
