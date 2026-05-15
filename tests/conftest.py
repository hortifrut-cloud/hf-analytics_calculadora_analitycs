"""
Archivo: conftest.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Orquestador de fixtures globales para la suite de pruebas de la Fase 2.
Centraliza la lógica de carga de "Golden Masters" desde archivos CSV y
la construcción del escenario canónico "UI.png". Este archivo asegura que
todos los tests (unitarios, de integración y E2E) operen sobre una base
de datos de referencia consistente y validada.

Acciones Principales:
    - Carga y parseo de archivos CSV históricos (`imagen1..10.csv`).
    - Definición del `scenario_ui_png` como objeto `ScenarioState` inmutable.
    - Exposición de subtotales "golden" para validaciones matemáticas.
    - Gestión de rutas relativas a la documentación técnica del proyecto.

Estructura Interna:
    - `scenario_ui_png`: Fixture de sesión que entrega el escenario maestro.
    - `base_table_imagen1`: Fixture que parsea la tabla base de Trujillo/Olmos.
    - `golden_imagenX`: Conjunto de fixtures que exponen valores de referencia.

Entradas / Dependencias:
    - `docs/image/*.csv`: Archivos de referencia de negocio.

Ejemplo de Integración:
    def test_logic(scenario_ui_png):
        assert scenario_ui_png.name == "UI.png demo"
"""

from pathlib import Path

import pandas as pd
import pytest

from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow,
    NewProjectCell,
    Rules,
    ScenarioState,
    Variety,
    VarietyParamRow,
)

_DOCS_IMAGE = Path(__file__).parent.parent / "docs" / "image"
SEASONS = ALL_SEASONS


# ---------------------------------------------------------------------------
# Helpers de parseo CSV
# ---------------------------------------------------------------------------


def _read_csv_raw(nombre: str) -> list[list[str]]:
    path = _DOCS_IMAGE / nombre
    rows = []
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(encoding=enc) as f:
                for line in f:
                    line = line.rstrip("\n")
                    if line.strip():
                        rows.append(line.split(","))
            break
        except UnicodeDecodeError:
            rows = []
    return rows


def _parse_subtotals_block(rows: list[list[str]]) -> dict[str, dict[str, float]]:
    """Extrae filas 'Sub total (...)' → dict[metric_key][season] = valor."""
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        if not row or not row[0].startswith("Sub total"):
            continue
        label = row[0].strip()
        values: dict[str, float] = {}
        for i, season in enumerate(SEASONS):
            col = i + 2  # offset: col0=label, col1=unidad, col2..7=seasons
            val = row[col].strip() if col < len(row) else ""
            values[season] = float(val) if val else 0.0
        result[label] = values
    return result


# ---------------------------------------------------------------------------
# A2.1.1 — Parser imagen1.csv → BaseTable
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_table_imagen1() -> BaseTable:
    rows_raw = _read_csv_raw("imagen1.csv")
    # header: Proyectos,unidad,T2627,...,Total
    # data rows until blank then variación
    project_rows = []
    variation_row: dict[str, float] = {}

    for raw in rows_raw[1:]:  # skip header
        if not raw or raw[0].strip() == "":
            continue
        label = raw[0].strip()
        if label == "variación":
            for i, season in enumerate(SEASONS):
                col = i + 2
                val = raw[col].strip() if col < len(raw) else ""
                variation_row[season] = float(val) if val else 0.0
            continue
        if label == "Total":
            continue
        # project row
        unit = raw[1].strip()
        values: dict[str, float] = {}
        for i, season in enumerate(SEASONS):
            col = i + 2
            val = raw[col].strip() if col < len(raw) else ""
            values[season] = float(val) if val else 0.0
        total_val = (
            float(raw[8].strip()) if len(raw) > 8 and raw[8].strip() else sum(values.values())
        )
        project_rows.append(
            BaseTableRow(project_name=label, unit=unit, values=values, total=total_val)
        )

    return BaseTable(rows=project_rows, variation=variation_row)


# ---------------------------------------------------------------------------
# A2.1.2 — Fixture scenario_ui_png (escenario canónico)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def v1_params() -> list[VarietyParamRow]:
    """V1 canónica de plan_maestro.md §Datos de referencia."""
    data = [
        (1, 2.0, 1.00),
        (2, 3.0, 1.00),
        (3, 4.0, 0.90),
        (4, 5.0, 0.80),
        (5, 5.0, 0.70),
        (6, 5.0, 0.60),
        (7, 5.0, 0.60),
    ]
    return [
        VarietyParamRow(
            plant_year=y,
            productividad=prod,
            densidad=6500.0,
            precio_estimado=4.0,
            pct_recaudacion=pct,
        )
        for y, prod, pct in data
    ]


@pytest.fixture(scope="session")
def scenario_ui_png(v1_params: list[VarietyParamRow]) -> ScenarioState:
    """ScenarioState exacto de UI.png.

    Hectáreas tomadas de los CSVs (fuente de verdad):
    - B1 CHAO  T2627=250
    - B1 OLMOS T2728=200
    - B2 OLMOS T2627=50   ← CSV imagen8 (no T2728 como en plan_maestro tabla)
    - B3 Talsa T2627=100, T2728=100
    - B3 Diamond Bridge T2627=25
    """
    return ScenarioState(
        name="UI.png demo",
        base_table=BaseTable(
            rows=[
                BaseTableRow(
                    project_name="Trujillo",
                    unit="tn",
                    values={s: v for s, v in zip(SEASONS, [37, 38, 39, 40, 41, 42])},
                    total=237.0,
                ),
                BaseTableRow(
                    project_name="Olmos",
                    unit="tn",
                    values={s: 8.0 for s in SEASONS},
                    total=48.0,
                ),
                BaseTableRow(
                    project_name="Productores Terceros",
                    unit="tn",
                    values={s: v for s, v in zip(SEASONS, [14, 15, 15, 15, 15, 15])},
                    total=89.0,
                ),
            ],
            variation={s: v for s, v in zip(SEASONS, [-7, -7, -7, -7, -7, 0])},
        ),
        varieties=[Variety(name="V1", params=v1_params)],
        rules=Rules(),
        new_project_cells=[
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="CHAO",
                variety_name="V1",
                season="T2627",
                hectareas=250,
            ),
            NewProjectCell(
                bloque=BloqueKind.CRECIMIENTO_HF,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2728",
                hectareas=200,
            ),
            NewProjectCell(
                bloque=BloqueKind.RECAMBIO_VARIETAL,
                sub_proyecto="OLMOS",
                variety_name="V1",
                season="T2627",
                hectareas=50,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2627",
                hectareas=100,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Talsa",
                variety_name="V1",
                season="T2728",
                hectareas=100,
            ),
            NewProjectCell(
                bloque=BloqueKind.NUEVOS_TERCEROS,
                sub_proyecto="Diamond Bridge",
                variety_name="V1",
                season="T2627",
                hectareas=25,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# A2.1.3 — Parsers de matrices imagen7..10.csv
# ---------------------------------------------------------------------------


def _parse_matrix_csv(nombre: str) -> dict[str, dict[str, float]]:
    """Devuelve subtotales como {metric_label: {season: value}}."""
    rows = _read_csv_raw(nombre)
    return _parse_subtotals_block(rows)


@pytest.fixture(scope="session")
def golden_imagen7() -> dict[str, dict[str, float]]:
    """Subtotales de imagen7.csv — Crecimiento HF."""
    return _parse_matrix_csv("imagen7.csv")


@pytest.fixture(scope="session")
def golden_imagen8() -> dict[str, dict[str, float]]:
    """Subtotales de imagen8.csv — Recambio varietal."""
    return _parse_matrix_csv("imagen8.csv")


@pytest.fixture(scope="session")
def golden_imagen9() -> dict[str, dict[str, float]]:
    """Subtotales de imagen9.csv — Nuevos Prod Terceros (HF side)."""
    return _parse_matrix_csv("imagen9.csv")


@pytest.fixture(scope="session")
def golden_imagen10() -> dict[str, dict[str, float]]:
    """Subtotales de imagen10.csv — Terceros para Totales."""
    return _parse_matrix_csv("imagen10.csv")
