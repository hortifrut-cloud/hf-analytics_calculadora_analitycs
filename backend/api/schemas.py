"""DTOs para request/response de la API Starlette.

Separados de los modelos de dominio para no exponer campos internos (id, created_at, etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domain.enums import BloqueKind
from backend.domain.inputs import SeasonCode


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


class ScenarioCreateIn(BaseModel):
    name: str = Field(min_length=1)
    country: str = "Perú"


class ScenarioSummary(BaseModel):
    id: int
    name: str


# ---------------------------------------------------------------------------
# Varieties
# ---------------------------------------------------------------------------


class VarietyParamIn(BaseModel):
    plant_year: int = Field(ge=1, le=7)
    productividad: float = Field(ge=0)
    densidad: float = Field(ge=0)
    precio_estimado: float = Field(ge=0)
    pct_recaudacion: float = Field(ge=0, le=1)


class VarietyIn(BaseModel):
    name: str = Field(min_length=1)
    params: list[VarietyParamIn] = Field(min_length=7, max_length=7)


class VarietyParamsUpdateIn(BaseModel):
    params: list[VarietyParamIn] = Field(min_length=7, max_length=7)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class RulesIn(BaseModel):
    royaltie_fob: float = Field(ge=0, le=1)
    costo_plantines: float = Field(ge=0)
    interes_financiamiento: float = Field(default=0.0, ge=0)
    financiamiento_anios: int = Field(ge=1, le=20)


class RulesOut(BaseModel):
    royaltie_fob: float
    costo_plantines: float
    interes_financiamiento: float
    financiamiento_anios: int


# ---------------------------------------------------------------------------
# New project cells
# ---------------------------------------------------------------------------


class NewProjectCellIn(BaseModel):
    bloque: BloqueKind
    sub_proyecto: str = Field(min_length=1)
    variety_name: str = Field(min_length=1)
    season: SeasonCode
    hectareas: float = Field(ge=0)
