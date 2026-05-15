import logging

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.domain.enums import ALL_SEASONS, BloqueKind, PlantYear, SeasonCode

_log = logging.getLogger(__name__)

_KNOWN_SUBPROYECTOS_B1_B2 = {"CHAO", "OLMOS"}
_KNOWN_SUBPROYECTOS_B3 = {"Talsa", "Diamond Bridge"}


class BaseTableRow(BaseModel):
    project_name: str
    unit: str
    values: dict[str, float]
    total: float

    @model_validator(mode="after")
    def _check_total(self) -> "BaseTableRow":
        computed = sum(self.values.values())
        if abs(computed - self.total) > 1:
            raise ValueError(
                f"'total' {self.total} difiere del sum de values {computed:.2f} en más de 1"
            )
        return self


class BaseTable(BaseModel):
    rows: list[BaseTableRow]
    variation: dict[str, float]


class VarietyParamRow(BaseModel):
    plant_year: PlantYear
    productividad: float = Field(ge=0)
    densidad: float = Field(ge=0)
    precio_estimado: float = Field(ge=0)
    pct_recaudacion: float = Field(ge=0, le=1)


class Variety(BaseModel):
    name: str = Field(min_length=1)
    params: list[VarietyParamRow]

    @model_validator(mode="after")
    def _check_years(self) -> "Variety":
        years = [p.plant_year for p in self.params]
        years_set = set(years)
        if years_set != set(range(1, 8)) or len(years) != 7:
            raise ValueError(
                f"Años de planta deben ser exactamente {{1..7}} sin duplicados, "
                f"se encontró: {sorted(years)}"
            )
        return self


class Rules(BaseModel):
    royaltie_fob: float = Field(default=0.12, ge=0, le=1)
    costo_plantines: float = Field(default=3.5, ge=0)
    interes_financiamiento: float = Field(default=0.0, ge=0)
    financiamiento_anios: int = Field(default=5, ge=1, le=20)


class NewProjectCell(BaseModel):
    bloque: BloqueKind
    sub_proyecto: str
    variety_name: str
    season: SeasonCode
    hectareas: float = Field(ge=0)


_VALID_SEASONS: frozenset[str] = frozenset(ALL_SEASONS)


class ScenarioState(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    country: str = "Perú"
    base_table: BaseTable
    varieties: list[Variety]
    rules: Rules
    new_project_cells: list[NewProjectCell]

    @model_validator(mode="after")
    def _check_variety_references(self) -> "ScenarioState":
        known = {v.name for v in self.varieties}
        for cell in self.new_project_cells:
            if cell.variety_name not in known:
                raise ValueError(f"Variedad '{cell.variety_name}' no existe en el escenario")
        return self

    @model_validator(mode="after")
    def _check_season_range(self) -> "ScenarioState":
        for cell in self.new_project_cells:
            if cell.season not in _VALID_SEASONS:
                raise ValueError(
                    f"Temporada '{cell.season}' fuera del rango válido {sorted(_VALID_SEASONS)}"
                )
        return self

    @model_validator(mode="after")
    def _warn_unknown_subproyectos(self) -> "ScenarioState":
        for cell in self.new_project_cells:
            if cell.bloque in (BloqueKind.CRECIMIENTO_HF, BloqueKind.RECAMBIO_VARIETAL):
                if cell.sub_proyecto not in _KNOWN_SUBPROYECTOS_B1_B2:
                    _log.warning("Sub-proyecto desconocido en B1/B2: '%s'", cell.sub_proyecto)
            elif cell.bloque == BloqueKind.NUEVOS_TERCEROS:
                if cell.sub_proyecto not in _KNOWN_SUBPROYECTOS_B3:
                    _log.warning("Sub-proyecto desconocido en B3: '%s'", cell.sub_proyecto)
        return self
