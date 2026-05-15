"""Tests E2E con Playwright — Flujo completo UI.png + persistencia tras reload.

Cubre T8.1 (setup), T8.2 (flujo UI.png) y T8.3 (recarga y persistencia).

Orden deliberado:
  - Los tests que solo leen (golden, reload) corren primero.
  - El test que modifica el DB (edit_ha) corre al final para no contaminar
    el estado que ven los otros tests.

El servidor arranca con el escenario canónico ya sembrado (ver conftest.py).
Golden values de plan_maestro.md §Datos de referencia.
"""

from __future__ import annotations

import json
import urllib.request

import pytest
from playwright.sync_api import Page, expect

# -------------------------------------------------------------------
# Constantes
# -------------------------------------------------------------------

SHINY_TIMEOUT = 20_000  # ms — Shiny tarda en conectar via WebSocket
DEBOUNCE_WAIT = 2_000  # ms — debounce 1.5s + margen generoso

# Golden values del escenario canónico (plan_maestro.md §Datos de referencia)
_TOTALES_GOLDEN = {
    "hf_fruta_T2728": "5,525",
    "hf_gan_T2728": "16,949",
    "ter_gan_T2728": "5,720",
}
_B1_GOLDEN = {
    "prod_T2728": "3,250",
    "gan_T2728": "13,000",
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _shiny(page: Page):
    """FrameLocator del iframe Shiny."""
    return page.frame_locator("iframe.shiny-frame")


def _wait_shiny_ready(page: Page) -> None:
    """Espera hasta que los datos de la tabla de Totales sean visibles.

    Paso 1 — título de sección: confirma que Shiny conectó via WebSocket.
    Paso 2 — primera <td> en Totales: confirma que el reactive terminó.
    """
    frame = _shiny(page)
    frame.locator(".section-title", has_text="SECCIÓN 5").wait_for(timeout=SHINY_TIMEOUT)
    frame.locator("#totals-totals_table td").first.wait_for(timeout=SHINY_TIMEOUT)


def _api_put(base_url: str, path: str, data: dict) -> None:
    """PUT directo a la API; bypass del debounce Shiny para restaurar estado."""
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    urllib.request.urlopen(req)


# -------------------------------------------------------------------
# T8.1 — Setup: la página abre correctamente
# -------------------------------------------------------------------


def test_astro_shell_loads(page: Page) -> None:
    """T8.1 AC: el test mínimo abre la página y el shell Astro se muestra."""
    page.goto("/")
    page.wait_for_selector("header", timeout=10_000)
    assert "Business Planning 2026" in page.locator("header").inner_text()

    iframe = page.locator("iframe.shiny-frame")
    expect(iframe).to_be_visible()
    assert iframe.get_attribute("src") == "./shiny/"


# -------------------------------------------------------------------
# T8.2 — Flujo completo UI.png (solo lectura — corren antes del edit)
# -------------------------------------------------------------------


def test_shiny_app_renders(page: Page) -> None:
    """T8.2: la app Shiny renderiza las 5 secciones."""
    page.goto("/")
    _wait_shiny_ready(page)
    frame = _shiny(page)

    for sec in ("SECCIÓN 1", "SECCIÓN 2", "SECCIÓN 3", "SECCIÓN 4", "SECCIÓN 5"):
        expect(frame.locator(".section-title", has_text=sec)).to_be_visible(timeout=SHINY_TIMEOUT)


def test_totals_golden_values(page: Page) -> None:
    """T8.2 AC: la Sección 5 muestra los valores golden de UI.png."""
    page.goto("/")
    _wait_shiny_ready(page)
    frame = _shiny(page)

    html = frame.locator("#totals-totals_table").inner_text()

    for key, val in _TOTALES_GOLDEN.items():
        assert val in html, f"Golden {key}={val} no encontrado. Tabla:\n{html[:400]}"


def test_b1_subtotals_golden(page: Page) -> None:
    """T8.2 AC: Sub-totales del Bloque 1 (Crecimiento HF) coinciden con goldens."""
    page.goto("/")
    _wait_shiny_ready(page)
    frame = _shiny(page)

    frame.locator("#new_projects-new_projects_content td").first.wait_for(timeout=SHINY_TIMEOUT)
    html = frame.locator("#new_projects-new_projects_content").inner_text()

    for key, val in _B1_GOLDEN.items():
        assert val in html, f"Golden B1 {key}={val} no encontrado. Div:\n{html[:400]}"


# -------------------------------------------------------------------
# T8.3 — Recarga y persistencia (antes del test que modifica)
# -------------------------------------------------------------------


def test_reload_preserves_values(page: Page) -> None:
    """T8.3 AC: tras reload los totales golden siguen ahí y no hay 404."""
    page.goto("/")
    _wait_shiny_ready(page)

    frame = _shiny(page)
    totals_before = frame.locator("#totals-totals_table").inner_text()

    # Recargar la página
    page.reload()
    _wait_shiny_ready(page)

    frame = _shiny(page)
    totals_after = frame.locator("#totals-totals_table").inner_text()

    # Los valores deben ser iguales antes y después del reload
    assert (
        totals_before.strip() == totals_after.strip()
    ), f"Valores cambiaron tras reload.\nAntes: {totals_before}\nDespués: {totals_after}"

    # Los golden values deben estar presentes
    assert "5,525" in totals_after, f"HF fruta T2728 perdido tras reload"
    assert "16,949" in totals_after, f"HF ganancia T2728 perdido tras reload"

    # Sin 404: el header Astro debe seguir visible
    expect(page.locator("header")).to_be_visible()
    assert "404" not in page.title()


def test_reload_no_absolute_path_error(page: Page) -> None:
    """T8.3 AC: navegar a /shiny/ directamente no produce 404."""
    response = page.goto("/shiny/")
    assert response is not None
    assert response.status < 400, f"HTTP {response.status} en /shiny/"


# -------------------------------------------------------------------
# T8.2 — Test de edición (corre al final — modifica y restaura el DB)
# -------------------------------------------------------------------


def test_edit_ha_updates_subtotals(page: Page, live_server: str) -> None:
    """T8.2 AC: editar una celda de ha dispara recálculo correcto tras debounce.

    Este test corre al final porque modifica el DB.
    El restore usa la API directamente para evitar race conditions del debounce.
    """
    page.goto("/")
    _wait_shiny_ready(page)
    frame = _shiny(page)

    chao = frame.locator("#new_projects-ha_crecimiento_hf_CHAO_T2627")
    chao.wait_for(state="visible", timeout=SHINY_TIMEOUT)

    try:
        # Cambiar CHAO T2627: 250 → 300
        chao.fill("300")
        chao.press("Tab")
        page.wait_for_timeout(DEBOUNCE_WAIT)

        # B1 prod T2728 debe cambiar: 300 × 13000/1000 = 3900 tn
        frame.locator("#new_projects-new_projects_content td").first.wait_for(timeout=SHINY_TIMEOUT)
        html = frame.locator("#new_projects-new_projects_content").inner_text()
        assert "3,900" in html, f"Esperado 3,900 con CHAO=300; contenido:\n{html[:400]}"

    finally:
        # Restaurar vía API (bypassa debounce Shiny — más confiable que UI)
        _api_put(
            live_server,
            "/api/scenarios/1/new-projects",
            {
                "bloque": "crecimiento_hf",
                "sub_proyecto": "CHAO",
                "variety_name": "V1",
                "season": "T2627",
                "hectareas": 250,
            },
        )
