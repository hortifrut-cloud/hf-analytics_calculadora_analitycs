"""
Archivo: derived.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Define los modelos de datos de salida (schemas Pydantic) que contienen los 
resultados procesados por el motor de cálculo analítico.

Acciones Principales:
    - Representación de cálculos unitarios por variedad y productor.
    - Estructuración de matrices temporales de producción y ganancia.
    - Consolidación de subtotales por bloque y totales generales del escenario.

Estructura Interna:
    - `CalculosVariedadCell`: Resultado unitario (Kg/ha, FOB/ha) para una variedad.
    - `MatrizSubyacente`: Datos crudos proyectados por año de planta y temporada.
    - `Subtotales`: Agrupación de resultados por bloque lógico y variedad.
    - `Totales`: Consolidado final de fruta y ganancia para Hortifrut y Terceros.
    - `DerivedState`: Objeto raíz que contiene todo el output del motor.

Ejemplo de Integración:
    from backend.domain.derived import DerivedState
    results = DerivedState(calculos_variedades=[...], totales=...)
"""

from pydantic import BaseModel, ConfigDict

from backend.domain.enums import BloqueKind, Productor


class CalculosVariedadCell(BaseModel):
    """
    Contiene los indicadores calculados para una combinación específica de 
    variedad, tipo de productor y año de planta.
    """

    model_config = ConfigDict(frozen=True)

    variety_name: str
    productor: Productor
    plant_year: int

    productividad_kg_ha: float
    ganancia_fob_ha: float

    # Campos específicos para esquemas de recaudación (HF_TERCEROS y TERCEROS)
    pct_recaudacion: float | None = None
    ganancia_venta_propia_ha: float | None = None
    ganancia_venta_productor_ha: float | None = None


class MatrizSubyacente(BaseModel):
    """
    Representa una proyección temporal bidimensional de un indicador técnico 
    (producción, ganancia o plantines) para un bloque y sub-proyecto.

    Attributes:
        data: Diccionario anidado donde la primera llave es el año de planta (1..7) 
              y la segunda es el código de temporada (SeasonCode).
    """

    model_config = ConfigDict(frozen=True)

    bloque: BloqueKind
    sub_proyecto: str
    variety_name: str
    kind: str  # 'produccion' | 'ganancia' | 'plantines'
    data: dict[int, dict[str, float]]

    def subtotal_by_season(self) -> dict[str, float]:
        """
        Calcula la suma vertical de los valores para cada temporada, 
        agregando todos los años de planta.

        Returns:
            dict: Mapeo de SeasonCode a valor total acumulado.
        """
        totals: dict[str, float] = {}
        for season_row in self.data.values():
            for season, val in season_row.items():
                totals[season] = totals.get(season, 0.0) + val
        return totals


class Subtotales(BaseModel):
    """
    Agrupación de resultados estacionales para una variedad dentro de un bloque específico.
    """

    model_config = ConfigDict(frozen=True)

    bloque: BloqueKind
    variety_name: str
    produccion_by_season: dict[str, float]
    ganancia_by_season: dict[str, float]
    plantines_by_season: dict[str, float] = {}


class Totales(BaseModel):
    """
    Consolidado de indicadores críticos a nivel de escenario, diferenciando 
    entre producción propia (Hortifrut) y de terceros.
    """

    model_config = ConfigDict(frozen=True)

    hortifrut_fruta_by_season: dict[str, float]
    hortifrut_ganancia_by_season: dict[str, float]
    terceros_fruta_by_season: dict[str, float]
    terceros_ganancia_by_season: dict[str, float]


class DerivedState(BaseModel):
    """
    Contenedor principal e inmutable que encapsula todos los resultados 
    generados por una ejecución del motor de cálculo.
    """

    model_config = ConfigDict(frozen=True)

    calculos_variedades: list[CalculosVariedadCell]
    matrices: list[MatrizSubyacente]
    subtotales: list[Subtotales]
    totales: Totales
