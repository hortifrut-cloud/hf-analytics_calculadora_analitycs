"""Motor §3.10 — Totales consolidados Hortifrut + Terceros.

HF_fruta(t)    = Σ_V (SubProd_B1 + SubProd_B2 + SubProd_B3_hft)
HF_ganancia(t) = Σ_V (SubGan_B1 + SubGan_B2 + SubGan_B3_hft + SubGanPlantines)
Terceros_fruta    = Σ_V SubProd_terceros
Terceros_ganancia = Σ_V SubGan_terceros
"""

from backend.domain.enums import ALL_SEASONS

SEASONS = ALL_SEASONS


def compute_totales(
    crecimiento: dict[str, dict[str, dict[str, float]]],
    recambio: dict[str, dict[str, dict[str, float]]],
    nuevos_terceros: dict[str, dict[str, dict[str, float]]],
    plantines: dict[str, dict[str, float]],
    terceros_totales: dict[str, dict[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    """Devuelve {'hf_fruta', 'hf_ganancia', 'terceros_fruta', 'terceros_ganancia'} por temporada."""
    hf_fruta: dict[str, float] = {s: 0.0 for s in SEASONS}
    hf_ganancia: dict[str, float] = {s: 0.0 for s in SEASONS}
    terceros_fruta: dict[str, float] = {s: 0.0 for s in SEASONS}
    terceros_ganancia: dict[str, float] = {s: 0.0 for s in SEASONS}

    all_varieties = (
        set(crecimiento)
        | set(recambio)
        | set(nuevos_terceros)
        | set(plantines)
        | set(terceros_totales)
    )

    for variety in all_varieties:
        for s in SEASONS:
            hf_fruta[s] += (
                crecimiento.get(variety, {}).get("produccion", {}).get(s, 0.0)
                + recambio.get(variety, {}).get("produccion", {}).get(s, 0.0)
                + nuevos_terceros.get(variety, {}).get("produccion", {}).get(s, 0.0)
            )
            hf_ganancia[s] += (
                crecimiento.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + recambio.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + nuevos_terceros.get(variety, {}).get("ganancia", {}).get(s, 0.0)
                + plantines.get(variety, {}).get(s, 0.0)
            )
            terceros_fruta[s] += terceros_totales.get(variety, {}).get("produccion", {}).get(s, 0.0)
            terceros_ganancia[s] += (
                terceros_totales.get(variety, {}).get("ganancia", {}).get(s, 0.0)
            )

    return {
        "hf_fruta": hf_fruta,
        "hf_ganancia": hf_ganancia,
        "terceros_fruta": terceros_fruta,
        "terceros_ganancia": terceros_ganancia,
    }
