"""
Archivo: exports.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Generador de exportaciones en formato Excel (.xlsx). Crea un libro de
trabajo con múltiples hojas detallando la configuración y resultados del
escenario analítico, utilizando estilos corporativos (Ciruela/Verde).

Acciones Principales:
    - Generación de hojas para Tabla Base, Variedades, Reglas y Proyectos.
    - Consolidación de totales y márgenes en una vista resumen.
    - Aplicación de formatos condicionales y estilos corporativos.

Estructura Interna:
    - `export_xlsx`: Handler que sirve el archivo descargable.
    - `_build_xlsx`: Motor de construcción del archivo Excel (XlsxWriter).

Integración UI:
    - Proporciona la funcionalidad de descarga de reportes para el usuario.
    - Es invocado por `routes.py` mediante una petición GET.
"""

import io

from starlette.requests import Request
from starlette.responses import Response

from backend.db.repos import RulesRepo, ScenarioRepo
from backend.domain.enums import ALL_SEASONS
from backend.logic.recompute import recompute

_CIRUELA = "#E7B6D1"
_VERDE = "#0E7C3E"
_SEASONS = ALL_SEASONS


def _get_session(request: Request):
    return request.app.state.SessionLocal()


def _hex_to_argb(hex_color: str) -> str:
    return "FF" + hex_color.lstrip("#").upper()


def _build_xlsx(state, derived: dict) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})

    # Formatos
    header_fmt = wb.add_format({"bold": True, "bg_color": _CIRUELA, "border": 1, "align": "center"})
    num_fmt = wb.add_format({"num_format": "#,##0", "border": 1, "align": "right"})
    num_dec_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"})
    text_fmt = wb.add_format({"bold": False, "border": 1})
    verde_fmt = wb.add_format({"font_color": _VERDE, "bold": True, "border": 1})
    subtotal_fmt = wb.add_format(
        {"bold": True, "italic": True, "bg_color": "#F2F2F2", "border": 1, "num_format": "#,##0"}
    )

    # ---------- Hoja 1: Tabla Base ----------
    ws1 = wb.add_worksheet("Tabla Base")
    ws1.write(0, 0, "Proyecto", header_fmt)
    ws1.write(0, 1, "Unidad", header_fmt)
    for col, s in enumerate(_SEASONS, start=2):
        ws1.write(0, col, s, header_fmt)
    ws1.write(0, len(_SEASONS) + 2, "Total", header_fmt)

    for row_idx, row in enumerate(state.base_table.rows, start=1):
        ws1.write(row_idx, 0, row.project_name, text_fmt)
        ws1.write(row_idx, 1, row.unit, text_fmt)
        for col, s in enumerate(_SEASONS, start=2):
            ws1.write(row_idx, col, row.values.get(s, 0), num_fmt)
        ws1.write(row_idx, len(_SEASONS) + 2, row.total, num_fmt)

    # Variación
    var_row = len(state.base_table.rows) + 1
    ws1.write(var_row, 0, "Variación", text_fmt)
    ws1.write(var_row, 1, "", text_fmt)
    for col, s in enumerate(_SEASONS, start=2):
        ws1.write(var_row, col, state.base_table.variation.get(s, 0), num_fmt)

    # ---------- Hoja 2: Variedades ----------
    ws2 = wb.add_worksheet("Variedades")
    vars_header = [
        "Variedad",
        "Año",
        "Productividad (Kg/p)",
        "Densidad (p/ha)",
        "Precio (FOB/kg)",
        "% Recaudación",
    ]
    for col, h in enumerate(vars_header):
        ws2.write(0, col, h, header_fmt)

    row_idx = 1
    for v in state.varieties:
        for p in v.params:
            ws2.write(row_idx, 0, v.name, text_fmt)
            ws2.write(row_idx, 1, p.plant_year, num_fmt)
            ws2.write(row_idx, 2, p.productividad, num_dec_fmt)
            ws2.write(row_idx, 3, p.densidad, num_fmt)
            ws2.write(row_idx, 4, p.precio_estimado, num_dec_fmt)
            ws2.write(row_idx, 5, p.pct_recaudacion, num_dec_fmt)
            row_idx += 1

    # ---------- Hoja 3: Reglas ----------
    ws3 = wb.add_worksheet("Reglas")
    ws3.write(0, 0, "Variable", header_fmt)
    ws3.write(0, 1, "Unidad", header_fmt)
    ws3.write(0, 2, "Valor", header_fmt)

    reglas = [
        ("Royaltie FOB", "% FOB", state.rules.royaltie_fob),
        ("Costo Plantines", "$/planta", state.rules.costo_plantines),
        ("Interés financiamiento", "%", state.rules.interes_financiamiento),
        ("Financiamiento", "años", state.rules.financiamiento_anios),
    ]
    for i, (var, unit, val) in enumerate(reglas, start=1):
        ws3.write(i, 0, var, text_fmt)
        ws3.write(i, 1, unit, text_fmt)
        ws3.write(i, 2, val, verde_fmt)

    # ---------- Hoja 4: Nuevos Proyectos ----------
    ws4 = wb.add_worksheet("Nuevos Proyectos")
    ws4.write(0, 0, "Bloque", header_fmt)
    ws4.write(0, 1, "Sub-proyecto", header_fmt)
    ws4.write(0, 2, "Variedad", header_fmt)
    ws4.write(0, 3, "Métrica", header_fmt)
    for col, s in enumerate(_SEASONS, start=4):
        ws4.write(0, col, s, header_fmt)

    row_idx = 1
    for bloque_key, varieties_data in derived.get("crecimiento", {}).items():
        for variety_key, metrics in varieties_data.items():
            ws4.write(row_idx, 0, "Crecimiento HF", text_fmt)
            ws4.write(row_idx, 1, bloque_key, text_fmt)
            ws4.write(row_idx, 2, variety_key, text_fmt)
            ws4.write(row_idx, 3, "Producción (tn)", subtotal_fmt)
            for col, s in enumerate(_SEASONS, start=4):
                ws4.write(row_idx, col, metrics.get("prod", {}).get(s, 0), subtotal_fmt)
            row_idx += 1
            ws4.write(row_idx, 3, "Ganancia (miles $)", subtotal_fmt)
            for col, s in enumerate(_SEASONS, start=4):
                ws4.write(row_idx, col, metrics.get("gan", {}).get(s, 0), subtotal_fmt)
            row_idx += 1

    # ---------- Hoja 5: Totales ----------
    ws5 = wb.add_worksheet("Totales")
    ws5.write(0, 0, "Categoría", header_fmt)
    ws5.write(0, 1, "Métrica", header_fmt)
    ws5.write(0, 2, "Unidad", header_fmt)
    for col, s in enumerate(_SEASONS, start=3):
        ws5.write(0, col, s, header_fmt)

    totales = derived.get("totales", {})
    rows_totales = [
        ("Hortifrut", "Total fruta", "tn", "hf_fruta"),
        ("Hortifrut", "Ganancia", "miles $", "hf_ganancia"),
        ("Terceros", "Total fruta", "tn", "terceros_fruta"),
        ("Terceros", "Ganancia", "miles $", "terceros_ganancia"),
    ]
    for i, (cat, metric, unit, key) in enumerate(rows_totales, start=1):
        ws5.write(i, 0, cat, text_fmt)
        ws5.write(i, 1, metric, text_fmt)
        ws5.write(i, 2, unit, text_fmt)
        season_data = totales.get(key, {})
        for col, s in enumerate(_SEASONS, start=3):
            ws5.write(i, col, season_data.get(s, 0), subtotal_fmt)

    wb.close()
    buf.seek(0)
    return buf.read()


async def export_xlsx(request: Request) -> Response:
    sid = int(request.path_params["id"])
    with _get_session(request) as session:
        repo = ScenarioRepo(session)
        state = repo.get(sid)
    if state is None:
        from starlette.responses import JSONResponse

        return JSONResponse({"detail": "Escenario no encontrado."}, status_code=404)

    derived = recompute(state)
    xlsx_bytes = _build_xlsx(state, derived)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="scenario_{sid}.xlsx"'},
    )
