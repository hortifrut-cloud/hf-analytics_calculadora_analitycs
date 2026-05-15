"""SECCIÓN 1 — Tabla Base (display + fila variación editable + [Confirmar Base])."""

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
        ui.tags.span("SECCIÓN 1 · TABLA BASE", class_="section-title"),
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
    _status_msg: reactive.Value[str] = reactive.value("")

    @render.ui
    def base_table_content() -> ui.Tag:
        state = state_fn()
        if state is None:
            return ui.p("Cargando…", class_="text-muted")

        bt = state.base_table
        confirmed = _confirmed.get()

        # Cabecera
        header = ui.tags.tr(
            ui.tags.th("Proyectos"),
            ui.tags.th("Unidad"),
            *[ui.tags.th(lbl) for lbl in _SEASON_LABELS],
            ui.tags.th("Total"),
        )

        # Filas de proyectos (solo-lectura)
        project_rows = []
        for row in bt.rows:
            cells = [ui.tags.td(row.project_name), ui.tags.td(row.unit)]
            for s in ALL_SEASONS:
                cells.append(ui.tags.td(_fmt(row.values.get(s, 0))))
            cells.append(ui.tags.td(_fmt(row.total), class_="fw-bold"))
            project_rows.append(ui.tags.tr(*cells))

        # Fila Total
        totals_by_season: dict[str, float] = {}
        for s in ALL_SEASONS:
            totals_by_season[s] = sum(
                row.values.get(s, 0.0) for row in bt.rows
            )
        grand_total = sum(totals_by_season.values())
        total_row_cells = [ui.tags.td(ui.tags.strong("Total")), ui.tags.td("tn")]
        for s in ALL_SEASONS:
            total_row_cells.append(ui.tags.td(ui.tags.strong(_fmt(totals_by_season[s]))))
        total_row_cells.append(ui.tags.td(ui.tags.strong(_fmt(grand_total))))
        total_row = ui.tags.tr(*total_row_cells, class_="total-row")

        # Fila variación (editable o bloqueada)
        variation_cells = [ui.tags.td("variación"), ui.tags.td("")]
        if confirmed:
            for s in ALL_SEASONS:
                variation_cells.append(ui.tags.td(_fmt(bt.variation.get(s, 0))))
            variation_cells.append(ui.tags.td(_fmt(sum(bt.variation.values()))))
        else:
            for i, s in enumerate(ALL_SEASONS):
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
    @reactive.event(input.confirm_base)
    def _on_confirm() -> None:
        _confirmed.set(True)
        _status_msg.set("Base confirmada.")
