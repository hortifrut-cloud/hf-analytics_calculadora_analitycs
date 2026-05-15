"""
Archivo: app.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Punto de entrada principal de la aplicación Shiny. Orquesta la interfaz de
usuario y la lógica del servidor, integrando los diferentes módulos
funcionales (Tabla Base, Variedades, Reglas, Proyectos y Totales) bajo un
estado reactivo unificado.

Acciones Principales:
    - Definición del layout fluido con CSS corporativo.
    - Orquestación de la reactividad central (estado actual y resultados).
    - Montaje de módulos Shiny independientes.
    - Gestión del selector de escenario activo.

Estructura Interna:
    - `app_ui`: Definición de la estructura visual de la aplicación.
    - `server`: Lógica de orquestación de eventos y flujos de datos.

Integración UI:
    - Este archivo es la raíz de la interfaz reactiva.
    - Es montado por la aplicación Starlette principal en `/shiny`.
"""

from __future__ import annotations

from pathlib import Path

from shiny import App, module, reactive, render, ui

from backend.shiny_app.modules.base_table import base_table_server, base_table_ui
from backend.shiny_app.modules.new_projects import new_projects_server, new_projects_ui
from backend.shiny_app.modules.rules_panel import rules_panel_server, rules_panel_ui
from backend.shiny_app.modules.totals import totals_server, totals_ui
from backend.shiny_app.modules.varieties_panel import (
    varieties_panel_server,
    varieties_panel_ui,
)
from backend.shiny_app.state import list_scenarios, load_scenario

_CSS_PATH = Path(__file__).parent / "styles.css"

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

app_ui = ui.page_fluid(
    ui.include_css(_CSS_PATH),
    ui.tags.div(
        ui.tags.h5(
            "Business Planning 2026 — Perú · T26/27 → T31/32",
            class_="hf-app-title",
        ),
        ui.output_ui("scenario_selector_bar"),
        class_="hf-app-header",
    ),
    # Sección 1 — Tabla Base
    ui.card(
        base_table_ui("base_table"),
        full_screen=False,
    ),
    # Secciones 2 + 3 — Variedades / Reglas (lado a lado)
    ui.layout_columns(
        ui.card(varieties_panel_ui("varieties"), style="min-height:360px;"),
        ui.card(rules_panel_ui("rules"), style="min-height:360px;"),
        col_widths=(7, 5),
    ),
    # Sección 4 — Nuevos Proyectos
    ui.card(
        new_projects_ui("new_projects"),
    ),
    # Sección 5 — Totales
    ui.card(
        totals_ui("totals"),
    ),
    title="HF Breeding Planner",
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


def server(input: ui.input, output: ui.output, session: ui.session) -> None:  # noqa: A002
    # --- Estado central ---
    initial_id = 1
    scenarios = list_scenarios()
    if scenarios:
        # Si el 1 no está en la lista, tomamos el primero disponible
        if not any(sid == 1 for sid, _ in scenarios):
            initial_id = scenarios[0][0]

    scenario_id: reactive.Value[int] = reactive.value(initial_id)
    _reload_counter: reactive.Value[int] = reactive.value(0)

    def trigger_reload() -> None:
        _reload_counter.set(_reload_counter.get() + 1)

    @reactive.calc
    def current_state():
        _ = _reload_counter.get()
        sid = scenario_id.get()
        return load_scenario(sid)

    @reactive.calc
    def current_derived():
        from backend.logic.recompute import recompute

        state = current_state()
        if state is None or not state.varieties:
            return None
        return recompute(state)

    # Snapshot del derived anterior — se captura justo ANTES de guardar reglas
    # para mostrar badges de delta (▲/▼) en Secciones 4 y 5
    _snapshot_derived: reactive.Value[dict | None] = reactive.value(None)

    def capture_snapshot() -> None:
        _snapshot_derived.set(current_derived())

    def get_snapshot() -> dict | None:
        return _snapshot_derived.get()

    # --- Selector de escenario en cabecera ---
    @render.ui
    def scenario_selector_bar() -> ui.Tag:
        scenarios = list_scenarios()
        if not scenarios:
            return ui.p("Sin escenarios en DB.", class_="text-muted")
        choices = {str(sid): name for sid, name in scenarios}
        return ui.layout_columns(
            ui.input_select(
                "scenario_id_select",
                "Escenario activo:",
                choices=choices,
                selected=str(scenario_id.get()),
            ),
            col_widths=(4,),
        )

    @reactive.effect
    @reactive.event(input.scenario_id_select)
    def _on_scenario_change() -> None:
        try:
            sid = int(input.scenario_id_select())
            scenario_id.set(sid)
            trigger_reload()
        except (ValueError, TypeError):
            pass

    # --- Montar módulos ---
    base_table_server(
        "base_table",
        state_fn=current_state,
        reload_fn=trigger_reload,
        scenario_id_rv=scenario_id,
    )
    varieties_panel_server(
        "varieties",
        state_fn=current_state,
        reload_fn=trigger_reload,
        scenario_id_rv=scenario_id,
    )
    rules_panel_server(
        "rules",
        state_fn=current_state,
        reload_fn=trigger_reload,
        scenario_id_rv=scenario_id,
        snapshot_fn=capture_snapshot,
    )
    new_projects_server(
        "new_projects",
        state_fn=current_state,
        derived_fn=current_derived,
        reload_fn=trigger_reload,
        scenario_id_rv=scenario_id,
        prev_derived_fn=get_snapshot,
    )
    totals_server(
        "totals",
        derived_fn=current_derived,
        prev_derived_fn=get_snapshot,
    )


app = App(app_ui, server)
