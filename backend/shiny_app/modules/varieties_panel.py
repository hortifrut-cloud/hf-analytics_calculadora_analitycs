"""
Archivo: varieties_panel.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny para la Sección 2: Datos Variedades. Implementa un sistema 
CRUD completo para la gestión de variedades y sus parámetros técnicos 
(productividad, densidad, precio, recaudación) proyectados a 7 años.

Acciones Principales:
    - Creación de nuevas variedades con parámetros iniciales.
    - Edición de parámetros técnicos existentes mediante grilla dinámica.
    - Eliminación de variedades con validación de dependencias (hectáreas).
    - Visualización de datos mediante acordeones plegables.

Estructura Interna:
    - `varieties_panel_ui`: Define el contenedor principal de la sección.
    - `varieties_panel_server`: Gestiona el flujo CRUD y la reactividad.
    - `_variety_form`: Generador modular del formulario de entrada de datos.

Integración UI:
    - Renderiza la Sección 2 del simulador.
    - Es invocado por `shiny_app/app.py` mediante `varieties_panel_ui` y `varieties_panel_server`.
"""

from __future__ import annotations

from typing import Callable

from shiny import module, reactive, render, ui

from backend.domain.inputs import VarietyParamRow
from backend.shiny_app.state import (
    create_variety,
    delete_variety,
    get_variety_id,
    update_variety_params,
    variety_has_ha,
)

_PARAM_FIELDS = [
    ("productividad", "Productividad", "Kg/planta"),
    ("densidad", "Densidad", "planta/ha"),
    ("precio_estimado", "Precio estimado", "FOB/kg"),
    ("pct_recaudacion", "% Recaud. terceros", "%"),
]
_YEARS = list(range(1, 8))


def _param_input_id(year: int, field: str, prefix: str = "") -> str:
    return f"{prefix}vp_{year}_{field}"


def _variety_form(
    prefix: str,
    default_vals: dict | None = None,
    name_val: str = "",
    readonly: bool = False,
) -> ui.Tag:
    """Genera el formulario de variedad (nombre + tabla 7×4 params)."""
    dv = default_vals or {}
    name_input = ui.input_text(
        f"{prefix}variety_name",
        "Nombre de la variedad:",
        value=name_val,
        placeholder="ej. V1",
        width="220px",
    )
    if readonly:
        name_input = ui.div(
            ui.tags.label("Nombre:"),
            ui.tags.strong(name_val),
        )

    year_headers = [ui.tags.th(f"Año {y}") for y in _YEARS]
    param_rows = []
    for field, label, unit in _PARAM_FIELDS:
        cells = [ui.tags.td(label), ui.tags.td(unit)]
        for y in _YEARS:
            default_v = dv.get(f"{field}_{y}", None)
            if field == "pct_recaudacion" and default_v is not None:
                default_v = round(default_v * 100, 2)
            cells.append(
                ui.tags.td(
                    ui.input_numeric(
                        _param_input_id(y, field, prefix),
                        "",
                        value=default_v,
                        min=0,
                        max=(100 if field == "pct_recaudacion" else None),
                        step=(0.5 if field == "pct_recaudacion" else 1),
                        width="75px",
                    )
                )
            )
        param_rows.append(ui.tags.tr(*cells))

    table = ui.tags.table(
        ui.tags.thead(
            ui.tags.tr(
                ui.tags.th("Variable"),
                ui.tags.th("Unidad"),
                *year_headers,
            )
        ),
        ui.tags.tbody(*param_rows),
        class_="hf-table",
        style="font-size:0.8rem;",
    )
    return ui.div(name_input, ui.tags.br(), table)


@module.ui
def varieties_panel_ui() -> ui.Tag:
    return ui.div(
        ui.tags.span("SECCIÓN 2 · DATOS VARIEDADES", class_="section-title"),
        ui.output_ui("varieties_content"),
    )


@module.server
def varieties_panel_server(
    input: ui.input,  # noqa: A002
    output: ui.output,
    session: ui.session,
    *,
    state_fn: Callable,
    reload_fn: Callable,
    scenario_id_rv: reactive.Value,
) -> None:
    _mode: reactive.Value[str] = reactive.value("view")  # "view" | "new" | "edit"
    _status_msg: reactive.Value[str] = reactive.value("")
    _pending_delete: reactive.Value[str | None] = reactive.value(None)

    @render.ui
    def varieties_content() -> ui.Tag:
        state = state_fn()
        if state is None:
            return ui.p("Cargando…", class_="text-muted")

        mode = _mode.get()
        varieties = state.varieties
        variety_names = [v.name for v in varieties]

        # --- Selector de variedad existente ---
        selector_row = ui.layout_columns(
            ui.input_action_button(
                "btn_add_variety",
                "+ Agregar variedad",
                class_="btn btn-sm btn-outline-success",
            ),
            ui.input_select(
                "selected_variety",
                "Variedad:",
                choices={"": "— seleccionar —", **{n: n for n in variety_names}},
                selected=variety_names[0] if variety_names else "",
            )
            if variety_names
            else ui.p("Sin variedades aún.", class_="text-muted"),
            col_widths=(4, 8),
        )

        status = ui.output_text("variety_status")

        if mode == "new":
            form = ui.card(
                ui.card_header("Nueva variedad"),
                _variety_form("new_"),
                ui.layout_columns(
                    ui.input_action_button(
                        "btn_done_new",
                        "Hecho",
                        class_="btn btn-sm btn-primary",
                    ),
                    ui.input_action_button(
                        "btn_cancel",
                        "Cancelar",
                        class_="btn btn-sm btn-secondary",
                    ),
                    col_widths=(3, 3),
                ),
            )
            return ui.div(selector_row, form, status)

        if mode == "edit" and variety_names:
            sel = input.selected_variety() if variety_names else ""
            v_obj = next((v for v in varieties if v.name == sel), None)
            if v_obj:
                dv: dict = {}
                for p in v_obj.params:
                    for field, _, _ in _PARAM_FIELDS:
                        dv[f"{field}_{p.plant_year}"] = getattr(p, field)
                form = ui.card(
                    ui.card_header(f"Editando: {sel}"),
                    _variety_form("edit_", default_vals=dv, name_val=sel, readonly=True),
                    ui.layout_columns(
                        ui.input_action_button(
                            "btn_done_edit",
                            "Guardar cambios",
                            class_="btn btn-sm btn-primary",
                        ),
                        ui.input_action_button(
                            "btn_cancel",
                            "Cancelar",
                            class_="btn btn-sm btn-secondary",
                        ),
                        ui.input_action_button(
                            "btn_delete_variety",
                            "Eliminar",
                            class_="btn btn-sm btn-danger",
                        ),
                        col_widths=(4, 3, 3),
                    ),
                    ui.output_ui("delete_warning"),
                )
                return ui.div(selector_row, form, status)

        # View mode: mostrar acordeón con variedades
        if not variety_names:
            return ui.div(
                selector_row,
                ui.p("No hay variedades. Usa '+ Agregar variedad' para crear una.", class_="hf-warning"),
                status,
            )

        panels = []
        for v in varieties:
            dv = {}
            for p in v.params:
                for field, _, _ in _PARAM_FIELDS:
                    dv[f"{field}_{p.plant_year}"] = getattr(p, field)
            # Show read-only table inside accordion
            panels.append(
                ui.accordion_panel(
                    v.name,
                    _variety_form(f"ro_{v.name}_", default_vals=dv, name_val=v.name, readonly=True),
                )
            )

        return ui.div(
            selector_row,
            ui.accordion(*panels, id="variety_accordion", open=False, multiple=True),
            ui.input_action_button(
                "btn_edit_variety",
                "Editar variedad seleccionada",
                class_="btn btn-sm btn-outline-primary mt-2",
            )
            if variety_names
            else ui.div(),
            status,
        )

    @render.ui
    def delete_warning() -> ui.Tag:
        v = _pending_delete.get()
        if v is None:
            return ui.div()
        return ui.div(
            ui.tags.p(
                f"⚠ ¿Eliminar '{v}'? Esta acción no se puede deshacer.",
                class_="hf-warning",
            ),
            ui.input_action_button(
                "btn_confirm_delete",
                "Confirmar eliminación",
                class_="btn btn-sm btn-danger",
            ),
        )

    @render.text
    def variety_status() -> str:
        return _status_msg.get()

    # --- Acción: iniciar nueva variedad ---
    @reactive.effect
    @reactive.event(input.btn_add_variety)
    def _on_add() -> None:
        _mode.set("new")
        _status_msg.set("")

    # --- Acción: cancelar ---
    @reactive.effect
    @reactive.event(input.btn_cancel)
    def _on_cancel() -> None:
        _mode.set("view")
        _status_msg.set("")
        _pending_delete.set(None)

    # --- Acción: iniciar edición ---
    @reactive.effect
    @reactive.event(input.btn_edit_variety)
    def _on_edit() -> None:
        state = state_fn()
        if not state or not state.varieties:
            return
        _mode.set("edit")
        _status_msg.set("")

    # --- Acción: guardar nueva variedad ---
    @reactive.effect
    @reactive.event(input.btn_done_new)
    def _on_done_new() -> None:
        sid = scenario_id_rv.get()
        name = (input.new_variety_name() or "").strip()
        if not name:
            _status_msg.set("⚠ El nombre de la variedad no puede estar vacío.")
            return

        params = _collect_params("new_")
        if params is None:
            _status_msg.set("⚠ Completa todos los parámetros (7 años × 4 variables).")
            return

        result = create_variety(sid, name, params)
        if result is None:
            _status_msg.set(f"⚠ Ya existe una variedad llamada '{name}'.")
            return

        _mode.set("view")
        _status_msg.set(f"✓ Variedad '{name}' creada.")
        reload_fn()

    # --- Acción: guardar edición ---
    @reactive.effect
    @reactive.event(input.btn_done_edit)
    def _on_done_edit() -> None:
        state = state_fn()
        if not state or not state.varieties:
            return
        try:
            sel = input.selected_variety()
        except Exception:
            return
        if not sel:
            return

        params = _collect_params("edit_")
        if params is None:
            _status_msg.set("⚠ Completa todos los parámetros.")
            return

        sid = scenario_id_rv.get()
        vid = get_variety_id(sid, sel)
        if vid is None:
            _status_msg.set("⚠ Variedad no encontrada.")
            return

        update_variety_params(vid, params)
        _mode.set("view")
        _status_msg.set(f"✓ Variedad '{sel}' actualizada.")
        reload_fn()

    # --- Acción: iniciar eliminación ---
    @reactive.effect
    @reactive.event(input.btn_delete_variety)
    def _on_delete_click() -> None:
        state = state_fn()
        if not state or not state.varieties:
            return
        try:
            sel = input.selected_variety()
        except Exception:
            return
        if not sel:
            return
        _pending_delete.set(sel)

    # --- Acción: confirmar eliminación ---
    @reactive.effect
    @reactive.event(input.btn_confirm_delete)
    def _on_confirm_delete() -> None:
        sel = _pending_delete.get()
        if not sel:
            return
        sid = scenario_id_rv.get()
        if variety_has_ha(sid, sel):
            _status_msg.set(
                f"⚠ Eliminando '{sel}' — sus ha asignadas también serán borradas."
            )
        vid = get_variety_id(sid, sel)
        if vid is not None:
            delete_variety(vid)
        _pending_delete.set(None)
        _mode.set("view")
        _status_msg.set(f"✓ Variedad '{sel}' eliminada.")
        reload_fn()

    def _collect_params(prefix: str) -> list[VarietyParamRow] | None:
        """Lee inputs del formulario y construye lista de VarietyParamRow."""
        params = []
        for y in _YEARS:
            row_vals: dict[str, float] = {}
            for field, _, _ in _PARAM_FIELDS:
                iid = _param_input_id(y, field, prefix)
                try:
                    v = getattr(input, iid)()
                except Exception:
                    return None
                if v is None:
                    return None
                row_vals[field] = float(v)
            try:
                params.append(
                    VarietyParamRow(
                        plant_year=y,
                        productividad=row_vals["productividad"],
                        densidad=row_vals["densidad"],
                        precio_estimado=row_vals["precio_estimado"],
                        pct_recaudacion=row_vals["pct_recaudacion"] / 100,
                    )
                )
            except Exception:
                return None
        return params if len(params) == 7 else None
