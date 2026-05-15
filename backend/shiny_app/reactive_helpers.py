"""Helpers reactivos: debounce y utilidades Shiny."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from shiny import reactive

T = TypeVar("T")


def debounce(value_fn: Callable[[], T], ms: int = 1500) -> reactive.Value[T]:
    """Devuelve un reactive.value que refleja value_fn con retraso de `ms` ms.

    Patrón: cada vez que value_fn() cambia, registra el tiempo. El valor
    estabilizado solo se publica cuando han pasado >= ms ms sin nuevos cambios.
    """
    delay = ms / 1000.0
    _pending: reactive.Value[dict] = reactive.value(
        {"val": value_fn(), "t": 0.0, "init": True}
    )
    _result: reactive.Value[T] = reactive.value(value_fn())
    _last_emitted: reactive.Value[object] = reactive.value(None)

    @reactive.effect
    def _capture() -> None:
        v = value_fn()
        _pending.set({"val": v, "t": time.monotonic(), "init": False})

    @reactive.effect
    def _flush() -> None:
        reactive.invalidate_later(delay)
        p = _pending.get()
        if p["init"]:
            return
        if time.monotonic() - p["t"] < delay - 0.05:
            return
        if p["val"] is _last_emitted.get():
            return
        _last_emitted.set(p["val"])
        _result.set(p["val"])

    return _result


def fmt_number(v: float | None, decimals: int = 0) -> str:
    """Formatea un número para mostrar en la UI (— para None/0)."""
    if v is None:
        return "—"
    if decimals == 0:
        return f"{v:,.0f}"
    return f"{v:,.{decimals}f}"
