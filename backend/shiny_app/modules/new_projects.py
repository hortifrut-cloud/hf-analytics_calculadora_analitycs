"""
Archivo: new_projects.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Módulo Shiny para la Sección 4: Nuevos Proyectos. Permite la edición de 
superficies plantadas (hectáreas) segmentadas por bloques (Crecimiento HF, 
Recambio Varietal, Nuevos Terceros) y sub-proyectos.

Acciones Principales:
    - Gestión de inputs numéricos para hectáreas por temporada.
    - Implementación de lógica debounce para persistencia automática en DB.
    - Renderizado de subtotales de producción y ganancia calculados.
    - Filtrado dinámico por variedad activa.

Estructura Interna:
    - `new_projects_ui`: Define el contenedor y el título de la sección.
    - `new_projects_server`: Gestiona la lógica de edición, debounce y renderizado.

Integración UI:
    - Renderiza la Sección 4 del simulador.
    - Es invocado por `shiny_app/app.py` mediante `new_projects_ui` y `new_projects_server`.
"""

from __future__ import annotations

import time
from typing import Callable

from shiny import module, reactive, render, ui

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import NewProjectCell
from backend.shiny_app.state import batch_upsert_ha_cells

_SEASON_LABELS = ["T26/27", "T27/28", "T28/29", "T29/30", "T30/31", "T31/32"]

_BLOQUE_META: dict[str, tuple[str, list[str]]] = {
    "crecimiento_hf": ("1. Crecimiento Hortifrut", ["CHAO", "OLMOS"]),
    "recambio_varietal": ("2. Recambio varietal", ["CHAO", "OLMOS"]),
    "nuevos_terceros": ("3. Nuevos Prod Terceros", ["Talsa", "Diamond Bridge"]),
}


def _ha_id(bloque: str, sub: str, season: str) -> str:
    return f"ha_{bloque}_{sub}_{season}".replace(" ", "_")


def _fmt(v: object) -> str:
    """
    Formatea un valor numérico para mostrar en celdas de subtotales.

    Distingue tres casos:
        - None / no comparable: "—" (sin dato calculado).
        - 0.0 exacto: "0" (cálculo corrió y dio cero, ej. sin ha asignadas).
        - Otros: "{valor:,.0f}".
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
def new_projects_ui() -> ui.Tag:
    return ui.div(
        ui.tags.span("SECCIÓN 4 · NUEVOS PROYECTOS", class_="section-title"),
        ui.output_ui("new_projects_content"),
    )


@module.server
def new_projects_server(
    input: ui.input,  # noqa: A002
    output: ui.output,
    session: ui.session,
    *,
    state_fn: Callable,
    derived_fn: Callable,
    reload_fn: Callable,
    scenario_id_rv: reactive.Value,
    prev_derived_fn: Callable,
) -> None:
    # Debounce state: pending ha changes
    _pending: reactive.Value[dict | None] = reactive.value(None)
    _last_saved: reactive.Value[dict | None] = reactive.value(None)

    @render.ui
    def new_projects_content() -> ui.Tag:
        state = state_fn()
        if state is None:
            return ui.p("Cargando…", class_="text-muted")

        if not state.varieties:
            return ui.div(
                ui.tags.p(
                    "Crea al menos una variedad (Sección 2) para habilitar Nuevos Proyectos.",
                    class_="hf-warning",
                ),
                title="Crea al menos una variedad para habilitar Nuevos Proyectos",
            )

        variety_names = [v.name for v in state.varieties]
        derived = derived_fn()
        prev_derived = prev_derived_fn()

        # Determinar variedad activa ANTES de construir el selector para que
        # selected= preserve la selección actual y no resetee al re-renderizar.
        try:
            sel_variety = input.variety_filter()
        except Exception:
            sel_variety = variety_names[0]
        if not sel_variety or sel_variety not in variety_names:
            sel_variety = variety_names[0]

        # Selector de variedad
        selector = ui.layout_columns(
            ui.input_select(
                "variety_filter",
                "Filtro Variedad:",
                choices={n: n for n in variety_names},
                selected=sel_variety,
            ),
            col_widths=(4,),
        )

        # Construir ha_dict para variedad activa
        ha_dict: dict[tuple[str, str, str], float] = {}
        for cell in state.new_project_cells:
            if cell.variety_name == sel_variety:
                ha_dict[(cell.bloque.value, cell.sub_proyecto, cell.season)] = cell.hectareas

        # Banner explicativo cuando la variedad seleccionada no tiene ha asignadas
        # en ningún bloque/temporada — evita confusión con "—" en sub-totales.
        total_ha_variedad = sum(ha_dict.values())
        empty_banner: ui.Tag | None = None
        if total_ha_variedad == 0:
            empty_banner = ui.tags.p(
                f"La variedad '{sel_variety}' aún no tiene hectáreas asignadas. "
                "Ingresa valores en las celdas ciruela para que los subtotales "
                "y los totales (Sección 5) se calculen.",
                class_="hf-warning",
            )

        bloque_cards = []
        for bloque_key, (bloque_label, subproyectos) in _BLOQUE_META.items():
            rows: list[ui.Tag] = []

            # Header de temporadas
            rows.append(
                ui.tags.tr(
                    ui.tags.th("Sub-proyecto"),
                    ui.tags.th("Unidad"),
                    *[ui.tags.th(lbl) for lbl in _SEASON_LABELS],
                )
            )

            # Filas de ha editables
            for sub in subproyectos:
                ha_cells = []
                for s in ALL_SEASONS:
                    iid = _ha_id(bloque_key, sub, s)
                    val = ha_dict.get((bloque_key, sub, s), 0.0)
                    ha_cells.append(
                        ui.tags.td(
                            ui.input_numeric(
                                iid,
                                "",
                                value=val,
                                min=0,
                                step=50,
                                width="80px",
                            ),
                            class_="ha-input",
                        )
                    )
                rows.append(
                    ui.tags.tr(ui.tags.td(sub), ui.tags.td("ha"), *ha_cells)
                )

            # Filas de subtotales (de derived state)
            sub_prod: dict[str, float] = {}
            sub_gan: dict[str, float] = {}
            sub_plant: dict[str, float] = {}
            prev_sub_prod: dict[str, float] = {}
            prev_sub_gan: dict[str, float] = {}
            prev_sub_plant: dict[str, float] = {}

            if derived:
                _bloque_result_key = {
                    "crecimiento_hf": "crecimiento",
                    "recambio_varietal": "recambio",
                    "nuevos_terceros": "nuevos_terceros",
                }[bloque_key]
                bloque_data = derived.get(_bloque_result_key, {}).get(sel_variety, {})
                sub_prod = bloque_data.get("produccion", {})
                sub_gan = bloque_data.get("ganancia", {})
                if bloque_key == "nuevos_terceros":
                    sub_plant = derived.get("plantines", {}).get(sel_variety, {})

            if prev_derived:
                _bloque_result_key_prev = {
                    "crecimiento_hf": "crecimiento",
                    "recambio_varietal": "recambio",
                    "nuevos_terceros": "nuevos_terceros",
                }[bloque_key]
                prev_bloque_data = prev_derived.get(_bloque_result_key_prev, {}).get(
                    sel_variety, {}
                )
                prev_sub_prod = prev_bloque_data.get("produccion", {})
                prev_sub_gan = prev_bloque_data.get("ganancia", {})
                if bloque_key == "nuevos_terceros":
                    prev_sub_plant = prev_derived.get("plantines", {}).get(sel_variety, {})

            def subtotal_row(
                label: str, unit: str, data: dict, prev_data: dict
            ) -> ui.Tag:
                cells: list[ui.Tag] = [ui.tags.td(label), ui.tags.td(unit)]
                for s in ALL_SEASONS:
                    cells.append(_delta_cell(data.get(s), prev_data.get(s)))
                return ui.tags.tr(*cells, class_="subtotal-row")

            rows.append(subtotal_row("Sub total (producción)", "tn", sub_prod, prev_sub_prod))
            rows.append(subtotal_row("Sub total (ganancia)", "miles $", sub_gan, prev_sub_gan))
            if bloque_key == "nuevos_terceros":
                rows.append(
                    subtotal_row(
                        "Sub total (ganancia plantines)", "miles $", sub_plant, prev_sub_plant
                    )
                )

            bloque_cards.append(
                ui.div(
                    ui.tags.p(ui.tags.strong(bloque_label)),
                    ui.tags.table(
                        ui.tags.tbody(*rows),
                        class_="hf-table",
                    ),
                    style="margin-bottom:16px;",
                )
            )

        children: list[ui.Tag] = [selector]
        if empty_banner is not None:
            children.append(empty_banner)
        children.extend(bloque_cards)
        return ui.div(*children)

    # -----------------------------------------------------------------------
    # Debounce: recoger cambios de inputs de ha
    # -----------------------------------------------------------------------

    @reactive.effect
    def _collect_ha() -> None:
        """Captura todos los valores de ha para la variedad activa."""
        state = state_fn()
        if not state or not state.varieties:
            return

        variety_names = [v.name for v in state.varieties]
        try:
            sel_variety = input.variety_filter()
        except Exception:
            sel_variety = variety_names[0] if variety_names else ""
        if not sel_variety or sel_variety not in variety_names:
            sel_variety = variety_names[0] if variety_names else ""
        if not sel_variety:
            return

        vals: dict[tuple[str, str, str], float] = {}
        for bloque_key, (_, subproyectos) in _BLOQUE_META.items():
            for sub in subproyectos:
                for s in ALL_SEASONS:
                    iid = _ha_id(bloque_key, sub, s)
                    try:
                        v = getattr(input, iid)()
                        vals[(bloque_key, sub, s)] = float(v or 0)
                    except Exception:
                        pass

        _pending.set(
            {"vals": vals, "variety": sel_variety, "t": time.monotonic()}
        )

    @reactive.effect
    def _debounced_flush() -> None:
        """
        Persiste solo las celdas que cambiaron desde el último guardado.

        Compara celda a celda contra `_last_saved` para construir la lista
        de cambios y llama `batch_upsert_ha_cells` una sola vez (6 queries
        en total, en lugar de N×8 queries individuales).
        """
        reactive.invalidate_later(1.5)
        p = _pending.get()
        if not p:
            return
        if time.monotonic() - p["t"] < 1.45:
            return

        last = _last_saved.get()
        # Comparación rápida del dict completo para el caso sin cambios
        if last and last.get("vals") == p["vals"] and last.get("variety") == p["variety"]:
            return

        sid = scenario_id_rv.get()
        variety = p["variety"]
        last_vals: dict = last.get("vals", {}) if last else {}

        # Solo procesar celdas que realmente cambiaron
        changed_cells: list[NewProjectCell] = []
        for (bloque_key, sub, season), ha in p["vals"].items():
            last_ha = last_vals.get((bloque_key, sub, season), 0.0)
            if abs(ha - last_ha) < 1e-9:  # Sin cambio
                continue
            try:
                changed_cells.append(
                    NewProjectCell(
                        bloque=BloqueKind(bloque_key),
                        sub_proyecto=sub,
                        variety_name=variety,
                        season=season,  # type: ignore[arg-type]
                        hectareas=ha,
                    )
                )
            except Exception:
                pass

        if changed_cells:
            try:
                batch_upsert_ha_cells(sid, changed_cells)
                _last_saved.set({"vals": p["vals"], "variety": variety})
                reload_fn()
            except Exception:
                pass
