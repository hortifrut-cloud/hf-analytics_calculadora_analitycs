"""
Archivo: calculos_variedades.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Motor de cálculo técnico-económico por variedad. Calcula las productividades 
(Kg/ha) y ganancias (FOB/ha) proyectadas para cada variedad y año de planta, 
considerando los tres tipos de productores definidos en el negocio.

Acciones Principales:
    - Cálculo de Kg/ha y FOB/ha para Hortifrut Interna.
    - Cálculo de esquemas de recaudación y venta propia para HF Terceros.
    - Cálculo de márgenes para productores Terceros externos.

Estructura Interna:
    - `CalcVarRow`: Data class con los resultados de las 3 columnas de productor.
    - `compute_calculos_variedades`: Genera el mapeo variedadxAño con sus métricas.

Ejemplo de Integración:
    from backend.logic.calculos_variedades import compute_calculos_variedades
    res = compute_calculos_variedades(varieties, rules)
"""

from dataclasses import dataclass

from backend.domain.inputs import Rules, Variety


@dataclass(frozen=True)
class CalcVarRow:
    """
    Estructura de datos que almacena los resultados técnicos y económicos 
    para una combinación específica de variedad y año de planta.
    """

    # HF Interna (§3.4.1)
    prod_hfi: float  # Kg/ha
    gan_hfi: float  # FOB/ha

    # HF Terceros (§3.4.2)
    prod_hft: float  # Kg/ha  = prod_hfi × pct_recaud
    gan_venta_propia_hft: float  # FOB/ha = prod_hft × precio × R
    gan_venta_productor_hft: float  # FOB/ha = prod_terceros × precio × R

    # Terceros externo (§3.4.3)
    prod_terceros: float  # Kg/ha  = prod_hfi × (1 - pct_recaud)
    gan_venta_hf_terceros: float  # FOB/ha = prod_hft × precio × (1-R)
    gan_venta_propia_terceros: float  # FOB/ha = prod_terceros × precio × (1-R)


def compute_calculos_variedades(
    varieties: list[Variety],
    rules: Rules,
) -> dict[tuple[str, int], CalcVarRow]:
    """
    Calcula la matriz de rendimientos y FOB por hectárea para todas las 
    variedades y años de vida del cultivo.

    Args:
        varieties (list[Variety]): Lista de variedades con sus parámetros técnicos.
        rules (Rules): Reglas de negocio globales (ej. % de royalty).

    Returns:
        dict[tuple[str, int], CalcVarRow]: Mapeo indexado por (nombre_variedad, año_planta).
    """
    R = rules.royaltie_fob
    result: dict[tuple[str, int], CalcVarRow] = {}

    for variety in varieties:
        for param in variety.params:
            n = param.plant_year
            pct = param.pct_recaudacion
            precio = param.precio_estimado

            prod_hfi = param.productividad * param.densidad
            gan_hfi = precio * prod_hfi

            prod_hft = prod_hfi * pct
            prod_terc = prod_hfi * (1.0 - pct)

            gan_venta_propia_hft = prod_hft * precio * R
            gan_venta_productor_hft = prod_terc * precio * R

            gan_venta_hf_terceros = prod_hft * precio * (1.0 - R)
            gan_venta_propia_terceros = prod_terc * precio * (1.0 - R)

            result[(variety.name, n)] = CalcVarRow(
                prod_hfi=prod_hfi,
                gan_hfi=gan_hfi,
                prod_hft=prod_hft,
                gan_venta_propia_hft=gan_venta_propia_hft,
                gan_venta_productor_hft=gan_venta_productor_hft,
                prod_terceros=prod_terc,
                gan_venta_hf_terceros=gan_venta_hf_terceros,
                gan_venta_propia_terceros=gan_venta_propia_terceros,
            )

    return result
