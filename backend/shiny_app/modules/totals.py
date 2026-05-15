"""
Archivo: totals.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny para la Sección 5: Tabla de Totales. Presenta una vista 
consolidada de los resultados del escenario, agrupando volúmenes de fruta y 
ganancias estimadas tanto para Hortifrut como para terceros.

Acciones Principales:
    - Renderizado de tabla de resumen ejecutivo (solo lectura).
    - Agrupación jerárquica de resultados (Hortifrut vs Terceros).
    - Actualización dinámica basada en el estado derivado (recálculo).

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
    if v is None:
        return "—"
    try:
        f = float(v)  # type: ignore[arg-type]
        if f == 0:
            return "—"
        return f"{f:,.0f}"
    except (TypeError, ValueError):
        return "—"


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
) -> None:
    @render.ui
    def totals_table() -> ui.Tag:
        derived = derived_fn()
        if derived is None:
            return ui.p(
                "Sin datos derivados. Crea al menos una variedad y asigna hectáreas.",
                class_="text-muted",
            )

        totales = derived.get("totales", {})
        hf_fruta = totales.get("hf_fruta", {})
        hf_gan = totales.get("hf_ganancia", {})
        ter_fruta = totales.get("terceros_fruta", {})
        ter_gan = totales.get("terceros_ganancia", {})

        def row(label: str, unit: str, data: dict) -> ui.Tag:
            cells = [ui.tags.td(label), ui.tags.td(unit)]
            for s in ALL_SEASONS:
                cells.append(ui.tags.td(_fmt(data.get(s))))
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
                        ui.tags.td(
                            ui.tags.strong("Hortifrut"),
                            colspan="8",
                            style="background:#e8f5e9;",
                        )
                    ),
                    row("  Total fruta", "tn", hf_fruta),
                    row("  Ganancia", "miles $", hf_gan),
                    ui.tags.tr(
                        ui.tags.td(
                            ui.tags.strong("Terceros"),
                            colspan="8",
                            style="background:#e8f5e9;",
                        )
                    ),
                    row("  Total fruta", "tn", ter_fruta),
                    row("  Ganancia", "miles $", ter_gan),
                ),
                class_="hf-table",
            )
        )
