"""
Archivo: totals.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny para la Sección 5: Tabla de Totales. Presenta una vista
consolidada de los resultados del escenario, agrupando volúmenes de fruta y
ganancias estimadas tanto para Hortifrut como para terceros. Incluye badges
de delta (▲/▼) que muestran el impacto del último guardado de Reglas.

Acciones Principales:
    - Renderizado de tabla de resumen ejecutivo (solo lectura).
    - Agrupación jerárquica de resultados (Hortifrut vs Terceros).
    - Actualización dinámica basada en el estado derivado (recálculo).
    - Visualización de variación KPI respecto al snapshot previo de Sección 3.

Estructura Interna:
    - `totals_ui`: Define la interfaz de la tabla de totales.
    - `totals_server`: Procesa el estado derivado para su visualización.

Integración UI:
    - Renderiza la Sección 5 del simulador.
    - Es invocado por `shiny_app/app.py` mediante `totals_ui` y `totals_server`.
"""

from __future__ import annotations

from typing import Callable

from shiny import module, reactive, render, ui

from backend.domain.enums import ALL_SEASONS

_SEASON_LABELS = ["T26/27", "T27/28", "T28/29", "T29/30", "T30/31", "T31/32"]


def _fmt(v: object) -> str:
    """
    Formatea un valor numérico para celdas de la tabla de totales.

    "—" se reserva para valores no calculables (None); 0.0 se muestra como "0"
    para evidenciar que el motor de cálculo corrió y dio cero (típicamente
    porque la variedad activa no tiene hectáreas asignadas).
    """
    if v is None:
        return "—"
    try:
        f = float(v)  # type: ignore[arg-type]
        return f"{f:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _delta_cell(val: object, prev_val: object) -> ui.Tag:
    """Celda con valor + badge de delta respecto al snapshot anterior."""
    formatted = _fmt(val)
    try:
        v = float(val or 0)  # type: ignore[arg-type]
        p = float(prev_val or 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ui.tags.td(formatted)
    delta = v - p
    if abs(delta) < 0.5:
        return ui.tags.td(formatted)
    arrow = "▲" if delta > 0 else "▼"
    css_class = "delta-up" if delta > 0 else "delta-down"
    return ui.tags.td(
        ui.div(
            ui.tags.span(formatted),
            ui.tags.span(f"{arrow} {abs(delta):,.0f}", class_=f"delta-badge {css_class}"),
            class_="delta-cell",
        )
    )


@module.ui
def totals_ui() -> ui.Tag:
    return ui.div(
        ui.tags.span("SECCIÓN 5 · TOTALES", class_="section-title"),
        ui.output_ui("totals_table"),
    )


@module.server
def totals_server(
    input: ui.input,  # noqa: A002
    output: ui.output,
    session: ui.session,
    *,
    derived_fn: Callable,
    prev_derived_fn: Callable,
) -> None:
    @render.ui
    def totals_table() -> ui.Tag:
        derived = derived_fn()
        if derived is None:
            return ui.p(
                "Sin datos derivados. Crea al menos una variedad y asigna hectáreas.",
                class_="text-muted",
            )

        prev_derived = prev_derived_fn()

        totales = derived.get("totales", {})
        hf_fruta = totales.get("hf_fruta", {})
        hf_gan = totales.get("hf_ganancia", {})
        ter_fruta = totales.get("terceros_fruta", {})
        ter_gan = totales.get("terceros_ganancia", {})

        prev_totales = prev_derived.get("totales", {}) if prev_derived else {}
        prev_hf_fruta = prev_totales.get("hf_fruta", {})
        prev_hf_gan = prev_totales.get("hf_ganancia", {})
        prev_ter_fruta = prev_totales.get("terceros_fruta", {})
        prev_ter_gan = prev_totales.get("terceros_ganancia", {})

        def row(label: str, unit: str, data: dict, prev_data: dict) -> ui.Tag:
            cells: list[ui.Tag] = [ui.tags.td(label), ui.tags.td(unit)]
            for s in ALL_SEASONS:
                cells.append(_delta_cell(data.get(s), prev_data.get(s)))
            return ui.tags.tr(*cells)

        return ui.div(
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Total"),
                        ui.tags.th("Unidad"),
                        *[ui.tags.th(lbl) for lbl in _SEASON_LABELS],
                    )
                ),
                ui.tags.tbody(
                    ui.tags.tr(
                        ui.tags.td("Hortifrut", colspan="8"),
                        class_="category-row",
                    ),
                    row("  Total fruta", "tn", hf_fruta, prev_hf_fruta),
                    row("  Ganancia", "miles $", hf_gan, prev_hf_gan),
                    ui.tags.tr(
                        ui.tags.td("Terceros", colspan="8"),
                        class_="category-row",
                    ),
                    row("  Total fruta", "tn", ter_fruta, prev_ter_fruta),
                    row("  Ganancia", "miles $", ter_gan, prev_ter_gan),
                ),
                class_="hf-table",
            ),
            class_="hf-section-wide",
        )
