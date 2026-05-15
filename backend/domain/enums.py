"""
Archivo: enums.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Define las enumeraciones y tipos literales fundamentales utilizados en todo el 
dominio del calculador analítico de Hortifrut.

Acciones Principales:
    - Definición de tipos de productores (Interno, Terceros).
    - Definición de bloques de lógica de negocio.
    - Definición de códigos de temporada y años de planta.

Estructura Interna:
    - `Productor`: Enum para clasificar el origen de la fruta.
    - `BloqueKind`: Enum para los tres bloques principales del motor.
    - `SeasonCode`: Literal con las 6 temporadas de planificación.

Ejemplo de Integración:
    from backend.domain.enums import Productor, BloqueKind
    tipo = Productor.HF_INTERNA
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field


class Productor(str, Enum):
    """
    Clasificación del origen y responsabilidad de la producción de fruta.
    """

    HF_INTERNA = "hf_interna"
    HF_TERCEROS = "hf_terceros"
    TERCEROS = "terceros"


class BloqueKind(str, Enum):
    """
    Tipos de bloques lógicos que componen el motor de cálculo.
    """

    CRECIMIENTO_HF = "crecimiento_hf"
    RECAMBIO_VARIETAL = "recambio_varietal"
    NUEVOS_TERCEROS = "nuevos_terceros"


# Tipos de datos especializados para validación Pydantic
SeasonCode = Literal["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]

PlantYear = Annotated[int, Field(ge=1, le=7)]

# Lista auxiliar para iteraciones
ALL_SEASONS: list[SeasonCode] = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
