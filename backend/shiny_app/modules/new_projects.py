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

import re
import time
from typing import Callable

from shiny import module, reactive, render, ui

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import NewProjectCell
from backend.shiny_app.state import (
    add_subproyecto,
    batch_upsert_ha_cells,
    remove_subproyecto,
)

_SEASON_LABELS = ["T26/27", "T27/28", "T28/29", "T29/30", "T30/31", "T31/32"]

# Etiqueta legible y sub-proyectos por defecto cuando el escenario aún no
# tiene ninguno persistido en DB.
_BLOQUE_LABELS: dict[str, str] = {
    "crecimiento_hf": "1. Crecimiento Hortifrut",
    "recambio_varietal": "2. Recambio varietal",
    "nuevos_terceros": "3. Nuevos Prod Terceros",
}
_DEFAULT_SUBPROYECTOS: dict[str, list[str]] = {
    "crecimiento_hf": ["CHAO", "OLMOS"],
    "recambio_varietal": ["CHAO", "OLMOS"],
    "nuevos_terceros": ["Talsa", "Diamond Bridge"],
}
_BLOQUE_KINDS: list[str] = list(_BLOQUE_LABELS.keys())


def _safe_id(text: str) -> str:
    """Sanitiza un string para usarlo como sufijo de input ID de Shiny."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_") or "x"


def _ha_id(bloque: str, sub: str, season: str) -> str:
    return f"ha_{bloque}_{_safe_id(sub)}_{season}"


def _del_id(bloque: str, sub: str) -> str:
    return f"btn_del_{bloque}_{_safe_id(sub)}"


def _add_btn_id(bloque: str) -> str:
    return f"btn_add_sub_{bloque}"


def _add_txt_id(bloque: str) -> str:
    return f"txt_add_sub_{bloque}"


def _subproyectos_for(state, bloque_key: str, variety_name: str) -> list[str]:
    """
    Resuelve la lista activa de sub-proyectos para (bloque, variedad).

    Si la variedad aún no tiene una lista persistida, devuelve los defaults
    del bloque. Cada variedad gestiona su lista de forma independiente.
    """
    if state is None or not variety_name:
        return list(_DEFAULT_SUBPROYECTOS[bloque_key])
    bloque_map = state.subproyectos.get(bloque_key) or {}
    labels = bloque_map.get(variety_name)
    if labels:
        return list(labels)
    return list(_DEFAULT_SUBPROYECTOS[bloque_key])


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
    # Debounce state: captura pendiente de hectáreas (vals + variedad + timestamp).
    # NOTA: ya no se mantiene un "_last_saved" comparado en memoria. La
    # comparación de cambios se hace contra el estado real de DB (state)
    # para evitar persistir capturas cruzadas entre variedades.
    _pending: reactive.Value[dict | None] = reactive.value(None)

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
        for bloque_key in _BLOQUE_KINDS:
            bloque_label = _BLOQUE_LABELS[bloque_key]
            subproyectos = _subproyectos_for(state, bloque_key, sel_variety)
            rows: list[ui.Tag] = []

            # Header de temporadas + columna para el botón de eliminar
            rows.append(
                ui.tags.tr(
                    ui.tags.th("Sub-proyecto"),
                    ui.tags.th("Unidad"),
                    *[ui.tags.th(lbl) for lbl in _SEASON_LABELS],
                    ui.tags.th(""),  # acción
                )
            )

            # Filas de ha editables (una por sub-proyecto)
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
                del_btn = ui.input_action_button(
                    _del_id(bloque_key, sub),
                    "✕",
                    class_="btn btn-sm btn-outline-danger btn-del-sub",
                    title=f"Eliminar sub-proyecto '{sub}' (borra sus hectáreas en todas las variedades)",
                )
                rows.append(
                    ui.tags.tr(
                        ui.tags.td(sub),
                        ui.tags.td("ha"),
                        *ha_cells,
                        ui.tags.td(del_btn, class_="sub-action-cell"),
                    )
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
                cells.append(ui.tags.td(""))  # columna acción vacía
                return ui.tags.tr(*cells, class_="subtotal-row")

            rows.append(subtotal_row("Sub total (producción)", "tn", sub_prod, prev_sub_prod))
            rows.append(subtotal_row("Sub total (ganancia)", "miles $", sub_gan, prev_sub_gan))
            if bloque_key == "nuevos_terceros":
                rows.append(
                    subtotal_row(
                        "Sub total (ganancia plantines)", "miles $", sub_plant, prev_sub_plant
                    )
                )

            # Pie del bloque: form inline para agregar nuevo sub-proyecto
            add_form = ui.div(
                ui.input_text(
                    _add_txt_id(bloque_key),
                    "",
                    placeholder="Nuevo sub-proyecto…",
                    width="220px",
                ),
                ui.input_action_button(
                    _add_btn_id(bloque_key),
                    "+ Agregar",
                    class_="btn btn-sm btn-outline-success",
                ),
                class_="add-sub-form",
            )

            bloque_cards.append(
                ui.div(
                    ui.tags.p(ui.tags.strong(bloque_label)),
                    ui.tags.table(
                        ui.tags.tbody(*rows),
                        class_="hf-table",
                    ),
                    add_form,
                    class_="bloque-card",
                )
            )

        children: list[ui.Tag] = [selector]
        if empty_banner is not None:
            children.append(empty_banner)
        children.extend(bloque_cards)
        return ui.div(*children, class_="hf-section-wide")

    # -----------------------------------------------------------------------
    # Debounce: recoger cambios de inputs de ha
    # -----------------------------------------------------------------------

    @reactive.effect
    def _collect_ha() -> None:
        """
        Captura los valores de hectáreas mostrados actualmente en pantalla.

        Solo crea dependencia reactiva sobre los inputs `ha_*` y el `state`.
        El `variety_filter` se lee dentro de `reactive.isolate()` para NO
        re-disparar la captura al cambiar el filtro — eso evita la carrera
        en la que se leerían inputs aún sin actualizar (valores de la
        variedad anterior) y se asociarían a la variedad nueva, persistiendo
        valores cruzados y provocando un bucle de re-render.
        """
        state = state_fn()
        if not state or not state.varieties:
            return

        variety_names = [v.name for v in state.varieties]
        with reactive.isolate():
            try:
                sel_variety = input.variety_filter()
            except Exception:
                sel_variety = variety_names[0]
        if not sel_variety or sel_variety not in variety_names:
            sel_variety = variety_names[0]

        vals: dict[tuple[str, str, str], float] = {}
        for bloque_key in _BLOQUE_KINDS:
            for sub in _subproyectos_for(state, bloque_key, sel_variety):
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
    @reactive.event(input.variety_filter, ignore_init=True)
    def _on_filter_change() -> None:
        """
        Al cambiar la variedad activa, descarta capturas pendientes que
        pudieran corresponder al estado anterior. Cuando la UI termine de
        re-renderizar, `_collect_ha` capturará los inputs actualizados.
        """
        _pending.set(None)

    @reactive.effect
    def _debounced_flush() -> None:
        """
        Persiste solo las celdas que difieren del estado guardado en DB.

        La comparación se hace contra `state.new_project_cells` (snapshot
        real cargado desde DB / caché) en lugar de un `_last_saved` en
        memoria. Esto garantiza que si por cualquier razón la captura
        pendiente refleja la variedad anterior, igual nada cambia (porque
        el diff contra DB para la nueva variedad será trivial) y el sistema
        converge en lugar de quedar en bucle.
        """
        reactive.invalidate_later(1.5)
        p = _pending.get()
        if not p:
            return
        if time.monotonic() - p["t"] < 1.45:
            return

        state = state_fn()
        if state is None:
            return

        variety = p["variety"]
        variety_names = {v.name for v in state.varieties}
        if variety not in variety_names:
            _pending.set(None)
            return

        # Snapshot real de hectáreas en DB para la variedad activa
        db_vals: dict[tuple[str, str, str], float] = {}
        for cell in state.new_project_cells:
            if cell.variety_name == variety:
                db_vals[(cell.bloque.value, cell.sub_proyecto, cell.season)] = cell.hectareas

        changed_cells: list[NewProjectCell] = []
        for (bloque_key, sub, season), ha in p["vals"].items():
            db_ha = db_vals.get((bloque_key, sub, season), 0.0)
            if abs(ha - db_ha) < 1e-9:
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

        # Consumir el pending pase lo que pase, para evitar reflush del mismo
        _pending.set(None)

        if changed_cells:
            sid = scenario_id_rv.get()
            try:
                batch_upsert_ha_cells(sid, changed_cells)
                reload_fn()
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Gestión de sub-proyectos (Agregar / Eliminar)
    # -----------------------------------------------------------------------

    def _active_variety_name(state) -> str:
        """Variedad actualmente seleccionada en el filtro (o la primera disponible)."""
        if state is None or not state.varieties:
            return ""
        names = [v.name for v in state.varieties]
        try:
            sel = input.variety_filter()
        except Exception:
            sel = names[0]
        if not sel or sel not in names:
            sel = names[0]
        return sel

    def _make_add_handler(bloque_key: str) -> Callable:
        """Crea un effect que reacciona al botón Agregar de un bloque concreto."""
        btn_id = _add_btn_id(bloque_key)
        txt_id = _add_txt_id(bloque_key)

        @reactive.effect
        @reactive.event(getattr(input, btn_id))
        def _on_add() -> None:
            sid = scenario_id_rv.get()
            try:
                raw = getattr(input, txt_id)()
            except Exception:
                return
            label = (raw or "").strip()
            if not label:
                return
            variety = _active_variety_name(state_fn())
            if not variety:
                return
            ok = add_subproyecto(sid, bloque_key, label, variety)
            if ok:
                reload_fn()

        return _on_add

    # Registramos un effect por bloque para los botones de agregar
    for _bk in _BLOQUE_KINDS:
        _make_add_handler(_bk)

    # Eliminar sub-proyecto: como los IDs son dinámicos (uno por sub-proyecto),
    # se hace polling de contadores de clicks contra los inputs presentes.
    _del_clicks: reactive.Value[dict[str, int]] = reactive.value({})

    @reactive.effect
    def _watch_delete_clicks() -> None:
        """Detecta clicks en cualquier botón ✕ de eliminación de sub-proyecto."""
        state = state_fn()
        if not state:
            return
        variety = _active_variety_name(state)
        if not variety:
            return
        sid = scenario_id_rv.get()
        prev = _del_clicks.get()
        new_counts = dict(prev)
        triggered: list[tuple[str, str]] = []
        for bloque_key in _BLOQUE_KINDS:
            for sub in _subproyectos_for(state, bloque_key, variety):
                iid = _del_id(bloque_key, sub)
                try:
                    n = int(getattr(input, iid)() or 0)
                except Exception:
                    continue
                if n > prev.get(iid, 0):
                    new_counts[iid] = n
                    triggered.append((bloque_key, sub))
        if triggered:
            # Persistir contadores ANTES de tocar DB para evitar bucles si
            # el reload re-dispara la effect en cascada.
            _del_clicks.set(new_counts)
            for bloque_key, sub in triggered:
                remove_subproyecto(sid, bloque_key, sub, variety)
            reload_fn()
