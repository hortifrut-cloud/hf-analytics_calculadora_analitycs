"""
Archivo: schemas.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Define los esquemas de validación y transferencia de datos (DTOs) utilizando
Pydantic. Estos modelos aseguran la integridad de las entradas y salidas de
la API, desacoplándolas de los modelos internos del dominio y de la base de datos.

Acciones Principales:
    - Validación de contratos de entrada para la creación de escenarios.
    - Definición de estructuras de respuesta para el listado de recursos.
    - Aplicación de restricciones de rango y formato mediante `Field`.

Estructura Interna:
    - `ScenarioCreateIn`: Esquema de entrada para nuevos escenarios.
    - `VarietyIn`: Estructura para definición de variedades y sus parámetros.
    - `RulesIn/Out`: Contratos para la gestión de reglas de negocio.
    - `NewProjectCellIn`: Validación para la actualización de celdas de proyecto.

Ejemplo de Integración:
    from backend.api.schemas import ScenarioCreateIn
    data = ScenarioCreateIn(**request_json)
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
