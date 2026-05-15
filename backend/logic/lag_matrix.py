"""
Archivo: lag_matrix.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de desfase fenológico. Implementa la lógica de retraso temporal (lag) 
para proyectar el impacto de las hectáreas plantadas en temporadas futuras, 
basándose en el ciclo de vida de la planta (1 a 7 años).

Sustentación Científica:
El cálculo sigue el principio de M[n, t] = ha(t - n), donde 'n' es la edad 
de la planta y 't' es la temporada actual. Se utiliza el método `shift` de 
Pandas para desplazar las series de tiempo eficientemente.

Acciones Principales:
    - Construcción de matrices de desfase para indicadores técnicos.
    - Agregación estacional de hectáreas por bloque y variedad.

Estructura Interna:
    - `build_lag_matrix`: Crea el DataFrame con la estructura plant_year x season.
    - `aggregate_ha`: Consolida la superficie plantada desde las celdas de entrada.

Ejemplo de Integración:
    from backend.logic.lag_matrix import build_lag_matrix
    matrix = build_lag_matrix(ha_dict, max_plant_year=7)
"""

import pandas as pd

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import NewProjectCell


def build_lag_matrix(
    ha_by_season: dict[str, float],
    max_plant_year: int,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    """
    Construye una matriz donde las filas representan la edad de la planta 
    y las columnas las temporadas de planificación.

    Args:
        ha_by_season (dict[str, float]): Diccionario con hectáreas plantadas por temporada.
        max_plant_year (int): Edad máxima de la planta (usualmente 7).
        seasons (list[str], opcional): Lista ordenada de temporadas. Por defecto usa ALL_SEASONS.

    Returns:
        pd.DataFrame: Matriz de desfase con índices 'plant_year' y columnas 'season'.
    """
    if seasons is None:
        seasons_list: list[str] = list(ALL_SEASONS)
    else:
        seasons_list = seasons
    base = pd.Series(ha_by_season, dtype=float).reindex(seasons_list).fillna(0.0)
    rows: dict[int, list[float]] = {}
    for n in range(1, max_plant_year + 1):
        shifted = base.shift(n, fill_value=0.0)
        rows[n] = shifted.tolist()
    df = pd.DataFrame(rows, index=seasons_list).T
    df.index.name = "plant_year"
    df.columns.name = "season"
    return df


def aggregate_ha(
    cells: list[NewProjectCell],
    bloque: BloqueKind,
    variety_name: str,
    seasons: list[str] | None = None,
) -> dict[str, float]:
    """
    Agrupa y suma la superficie (ha) de todos los sub-proyectos para una 
    combinación específica de bloque y variedad.

    Args:
        cells (list[NewProjectCell]): Lista de celdas con datos de hectáreas.
        bloque (BloqueKind): Tipo de bloque a filtrar.
        variety_name (str): Nombre de la variedad a filtrar.
        seasons (list[str], opcional): Lista de temporadas objetivo.

    Returns:
        dict[str, float]: Mapeo de temporada a total de hectáreas agregadas.
    """
    if seasons is None:
        seasons_list: list[str] = list(ALL_SEASONS)
    else:
        seasons_list = seasons

    totals: dict[str, float] = {s: 0.0 for s in seasons_list}
    for cell in cells:
        if cell.bloque == bloque and cell.variety_name == variety_name:
            if cell.season in totals:
                totals[cell.season] += cell.hectareas
    return totals
