"""Motor §3.4 — Tabla cálculos variedades.

Para cada (variety, plant_year) calcula productividades y ganancias por ha
para los tres tipos de productor: HF_INTERNA, HF_TERCEROS, TERCEROS.
Todas las magnitudes en unidades base (Kg/ha, FOB/ha) — la división /1000 se
aplica más tarde al construir la matriz subyacente.
"""

from dataclasses import dataclass

from backend.domain.inputs import Rules, Variety


@dataclass(frozen=True)
class CalcVarRow:
    """Resultados por (variety_name, plant_year) — las 3 columnas de productor."""

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
    """Devuelve {(variety_name, plant_year): CalcVarRow} para cada variedad×año."""
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
