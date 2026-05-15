"""
Archivo: rules_panel.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny para la Sección 3: Reglas / Definiciones. Gestiona la edición 
de parámetros globales del escenario, como porcentajes de royalties, costos 
de plantines y condiciones de financiamiento.

Acciones Principales:
    - Renderizado de formulario técnico para parámetros de negocio.
    - Validación de campos obligatorios antes del guardado.
    - Persistencia directa de reglas en la base de datos.
    - Notificación de estados (éxito/error) al usuario.

Estructura Interna:
    - `rules_panel_ui`: Define la interfaz del panel de reglas.
    - `rules_panel_server`: Gestiona la lógica de entrada y persistencia.

Integración UI:
    - Renderiza la Sección 3 del simulador.
    - Es invocado por `shiny_app/app.py` mediante `rules_panel_ui` y `rules_panel_server`.
"""

from __future__ import annotations

from typing import Callable

from shiny import module, reactive, render, ui

from backend.domain.inputs import Rules
from backend.shiny_app.state import save_rules


@module.ui
def rules_panel_ui() -> ui.Tag:
    return ui.div(
        ui.tags.span("SECCIÓN 3 · REGLAS / DEFINICIONES", class_="section-title"),
        ui.output_ui("rules_form"),
    )


@module.server
def rules_panel_server(
    input: ui.input,  # noqa: A002
    output: ui.output,
    session: ui.session,
    *,
    state_fn: Callable,
    reload_fn: Callable,
    scenario_id_rv: reactive.Value,
    snapshot_fn: Callable,
) -> None:
    @render.ui
    def rules_form() -> ui.Tag:
        state = state_fn()
        if state is None:
            return ui.p("Cargando…", class_="text-muted")

        r = state.rules
        return ui.div(
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Variable"),
                        ui.tags.th("Unidad"),
                        ui.tags.th("Valor"),
                    )
                ),
                ui.tags.tbody(
                    ui.tags.tr(
                        ui.tags.td("Royaltie FOB"),
                        ui.tags.td("% FOB"),
                        ui.tags.td(
                            ui.input_numeric(
                                "royaltie_fob",
                                "",
                                value=round(r.royaltie_fob * 100, 4),
                                min=0,
                                max=100,
                                step=0.1,
                                width="100px",
                            ),
                            class_="rules-input",
                        ),
                    ),
                    ui.tags.tr(
                        ui.tags.td("Costo Plantines"),
                        ui.tags.td("$/planta"),
                        ui.tags.td(
                            ui.input_numeric(
                                "costo_plantines",
                                "",
                                value=r.costo_plantines,
                                min=0,
                                step=0.1,
                                width="100px",
                            ),
                            class_="rules-input",
                        ),
                    ),
                    ui.tags.tr(
                        ui.tags.td("Interés financiamiento"),
                        ui.tags.td("%"),
                        ui.tags.td(
                            ui.input_numeric(
                                "interes",
                                "",
                                value=round(r.interes_financiamiento * 100, 4),
                                min=0,
                                max=100,
                                step=0.1,
                                width="100px",
                            ),
                            class_="rules-input",
                        ),
                    ),
                    ui.tags.tr(
                        ui.tags.td("Financiamiento"),
                        ui.tags.td("años"),
                        ui.tags.td(
                            ui.input_numeric(
                                "financiamiento_anios",
                                "",
                                value=r.financiamiento_anios,
                                min=1,
                                max=20,
                                step=1,
                                width="100px",
                            ),
                            class_="rules-input",
                        ),
                    ),
                ),
                class_="hf-table",
            ),
            ui.input_action_button(
                "save_rules", "Guardar Reglas", class_="btn btn-sm btn-success mt-2"
            ),
            ui.output_text("rules_status"),
        )

    _status_msg: reactive.Value[str] = reactive.value("")

    @render.text
    def rules_status() -> str:
        return _status_msg.get()

    @reactive.effect
    @reactive.event(input.save_rules)
    def _on_save() -> None:
        sid = scenario_id_rv.get()
        try:
            royaltie_raw = input.royaltie_fob()
            costo_raw = input.costo_plantines()
            interes_raw = input.interes()
            fin_raw = input.financiamiento_anios()

            if any(v is None for v in [royaltie_raw, costo_raw, interes_raw, fin_raw]):
                _status_msg.set("⚠ Completa todos los campos antes de guardar.")
                return

            rules = Rules(
                royaltie_fob=float(royaltie_raw) / 100,
                costo_plantines=float(costo_raw),
                interes_financiamiento=float(interes_raw) / 100,
                financiamiento_anios=int(fin_raw),
            )
            snapshot_fn()   # captura derived actual antes de recomputar
            save_rules(sid, rules)
            reload_fn()
            _status_msg.set("✓ Reglas guardadas.")
        except Exception as exc:
            _status_msg.set(f"Error: {exc}")
