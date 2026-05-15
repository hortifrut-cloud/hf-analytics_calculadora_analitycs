"""
Archivo: base_table.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny que renderiza la Sección 1: Tabla Base. Muestra los volúmenes
proyectados por proyecto y temporada, permitiendo la edición de una fila
de variación y el bloqueo de la base mediante confirmación. Incluye
botón de plegar/expandir para ocultar la sección sin perder el estado.

Acciones Principales:
    - Renderizado dinámico de la grilla de proyectos (tn por temporada).
    - Gestión de inputs numéricos para la fila de variación.
    - Implementación de lógica de bloqueo "Confirmar Base".
    - Toggle de visibilidad de la sección (plegar/expandir).

Estructura Interna:
    - `base_table_ui`: Define la interfaz visual (header colapsable + contenedor).
    - `base_table_server`: Orquesta el estado reactivo y la renderización.

Integración UI:
    - Renderiza la Sección 1 del simulador.
    - Es invocado por `shiny_app/app.py` mediante `base_table_ui` y `base_table_server`.
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
        return f"{f:,.0f}"
    except (TypeError, ValueError):
        return str(v)


@module.ui
def base_table_ui() -> ui.Tag:
    return ui.div(
        ui.output_ui("base_table_header"),
        ui.output_ui("base_table_content"),
        ui.output_text("base_table_status"),
    )


@module.server
def base_table_server(
    input: ui.input,  # noqa: A002
    output: ui.output,
    session: ui.session,
    *,
    state_fn: Callable,
    reload_fn: Callable,
    scenario_id_rv: reactive.Value,
) -> None:
    _confirmed: reactive.Value[bool] = reactive.value(False)
    _collapsed: reactive.Value[bool] = reactive.value(False)
    _status_msg: reactive.Value[str] = reactive.value("")

    @render.ui
    def base_table_header() -> ui.Tag:
        collapsed = _collapsed.get()
        btn_label = "Mostrar ▼" if collapsed else "Ocultar ▲"
        return ui.div(
            ui.tags.span("SECCIÓN 1 · TABLA BASE", class_="section-title"),
            ui.input_action_button(
                "toggle_collapse",
                btn_label,
                class_="btn-collapse",
            ),
            class_="section-header",
        )

    @render.ui
    def base_table_content() -> ui.Tag:
        if _collapsed.get():
            return ui.div()

        state = state_fn()
        if state is None:
            return ui.p("Cargando…", class_="text-muted")

        bt = state.base_table
        confirmed = _confirmed.get()

        header = ui.tags.tr(
            ui.tags.th("Proyectos"),
            ui.tags.th("Unidad"),
            *[ui.tags.th(lbl) for lbl in _SEASON_LABELS],
            ui.tags.th("Total"),
        )

        project_rows = []
        for row in bt.rows:
            cells = [ui.tags.td(row.project_name), ui.tags.td(row.unit)]
            for s in ALL_SEASONS:
                cells.append(ui.tags.td(_fmt(row.values.get(s, 0))))
            cells.append(ui.tags.td(_fmt(row.total), class_="fw-bold"))
            project_rows.append(ui.tags.tr(*cells))

        totals_by_season: dict[str, float] = {}
        for s in ALL_SEASONS:
            totals_by_season[s] = sum(row.values.get(s, 0.0) for row in bt.rows)
        grand_total = sum(totals_by_season.values())
        total_row_cells = [ui.tags.td(ui.tags.strong("Total")), ui.tags.td("tn")]
        for s in ALL_SEASONS:
            total_row_cells.append(ui.tags.td(ui.tags.strong(_fmt(totals_by_season[s]))))
        total_row_cells.append(ui.tags.td(ui.tags.strong(_fmt(grand_total))))
        total_row = ui.tags.tr(*total_row_cells, class_="total-row")

        variation_cells = [ui.tags.td("variación"), ui.tags.td("")]
        if confirmed:
            for s in ALL_SEASONS:
                variation_cells.append(ui.tags.td(_fmt(bt.variation.get(s, 0))))
            variation_cells.append(ui.tags.td(_fmt(sum(bt.variation.values()))))
        else:
            for s in ALL_SEASONS:
                variation_cells.append(
                    ui.tags.td(
                        ui.input_numeric(
                            f"var_{s}",
                            "",
                            value=bt.variation.get(s, 0),
                            step=1,
                            width="80px",
                        ),
                        class_="ha-input",
                    )
                )
            variation_cells.append(ui.tags.td("—"))
        variation_row = ui.tags.tr(*variation_cells)

        table = ui.tags.table(
            ui.tags.thead(header),
            ui.tags.tbody(*project_rows, total_row, variation_row),
            class_="hf-table",
        )

        if not confirmed:
            btn = ui.input_action_button(
                "confirm_base",
                "Confirmar Base",
                class_="btn btn-sm btn-primary mt-2",
            )
            return ui.div(table, btn)
        else:
            return ui.div(
                table,
                ui.tags.span("✓ Base confirmada (solo lectura)", class_="text-verde"),
            )

    @render.text
    def base_table_status() -> str:
        return _status_msg.get()

    @reactive.effect
    @reactive.event(input.toggle_collapse)
    def _on_toggle() -> None:
        _collapsed.set(not _collapsed.get())

    @reactive.effect
    @reactive.event(input.confirm_base)
    def _on_confirm() -> None:
        _confirmed.set(True)
        _status_msg.set("Base confirmada.")
