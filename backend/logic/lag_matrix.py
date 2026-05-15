"""Motor §3.5 — Desfase fenológico (lag t → t+n).

M[n, t] = ha(t − n): las hectáreas plantadas n temporadas antes de t.
Implementado con DataFrame.shift(n) sobre el eje de temporadas.
"""

import pandas as pd

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import NewProjectCell


def build_lag_matrix(
    ha_by_season: dict[str, float],
    max_plant_year: int,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    """Devuelve DataFrame con filas=plant_year (1..max) y columnas=seasons.

    M[n, t] = ha en season (t - n), o 0 si t-n está fuera del rango.
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
    """Suma ha de todos los sub-proyectos de un bloque/variedad por temporada."""
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
