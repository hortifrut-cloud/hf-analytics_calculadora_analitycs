from enum import Enum
from typing import Annotated, Literal

from pydantic import Field


class Productor(str, Enum):
    HF_INTERNA = "hf_interna"
    HF_TERCEROS = "hf_terceros"
    TERCEROS = "terceros"


class BloqueKind(str, Enum):
    CRECIMIENTO_HF = "crecimiento_hf"
    RECAMBIO_VARIETAL = "recambio_varietal"
    NUEVOS_TERCEROS = "nuevos_terceros"


SeasonCode = Literal["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]

PlantYear = Annotated[int, Field(ge=1, le=7)]

ALL_SEASONS: list[SeasonCode] = ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
