from pydantic import BaseModel, ConfigDict

from backend.domain.enums import BloqueKind, Productor


class CalculosVariedadCell(BaseModel):
    """Resultado de cálculo para una combinación (variety, productor, plant_year)."""

    model_config = ConfigDict(frozen=True)

    variety_name: str
    productor: Productor
    plant_year: int

    productividad_kg_ha: float
    ganancia_fob_ha: float

    # Solo para HF_TERCEROS y TERCEROS
    pct_recaudacion: float | None = None
    ganancia_venta_propia_ha: float | None = None
    ganancia_venta_productor_ha: float | None = None


class MatrizSubyacente(BaseModel):
    """Matriz plant_year × season para un bloque/variedad/indicador.

    data[plant_year][season_code] → valor en miles (ton/mil o USD/mil).
    """

    model_config = ConfigDict(frozen=True)

    bloque: BloqueKind
    sub_proyecto: str
    variety_name: str
    kind: str  # 'produccion' | 'ganancia' | 'plantines'
    data: dict[int, dict[str, float]]

    def subtotal_by_season(self) -> dict[str, float]:
        """Suma sobre plant_years para cada season."""
        totals: dict[str, float] = {}
        for season_row in self.data.values():
            for season, val in season_row.items():
                totals[season] = totals.get(season, 0.0) + val
        return totals


class Subtotales(BaseModel):
    """Sub-totales por temporada para un bloque+variedad."""

    model_config = ConfigDict(frozen=True)

    bloque: BloqueKind
    variety_name: str
    produccion_by_season: dict[str, float]
    ganancia_by_season: dict[str, float]
    plantines_by_season: dict[str, float] = {}


class Totales(BaseModel):
    """Totales consolidados Hortifrut y Terceros."""

    model_config = ConfigDict(frozen=True)

    hortifrut_fruta_by_season: dict[str, float]
    hortifrut_ganancia_by_season: dict[str, float]
    terceros_fruta_by_season: dict[str, float]
    terceros_ganancia_by_season: dict[str, float]


class DerivedState(BaseModel):
    """Contenedor de todo el estado derivado del motor de cálculo."""

    model_config = ConfigDict(frozen=True)

    calculos_variedades: list[CalculosVariedadCell]
    matrices: list[MatrizSubyacente]
    subtotales: list[Subtotales]
    totales: Totales
