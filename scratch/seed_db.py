"""
Archivo: seed_db.py
Fecha de modificación: 15/05/2026
Autor: Alex Prieto

Descripción:
Script de utilidad para poblar la base de datos con el escenario de referencia
completo que replica exactamente los datos de docs/image/imagen1-6.csv.
Este seed es el punto de partida oficial de la aplicación para el plan de
negocio HF Perú 2026.

Acciones Principales:
    - Limpieza de escenarios anteriores (modo forzado).
    - Creación del escenario base con Tabla Base, Variedad 1, Reglas y Nuevos Proyectos.
    - Validación de la estructura creada mediante ScenarioRepo.get().

Ejecución:
    uv run python scratch/seed_db.py

Argumentos:
    - (ninguno): El script corre sin argumentos. Limpia la DB antes de insertar.
"""

from sqlalchemy.orm import Session

from backend.db.session import make_engine, make_session_factory
from backend.db.repos import ScenarioRepo
from backend.domain.inputs import (
    BaseTable,
    BaseTableRow,
    NewProjectCell,
    Rules,
    ScenarioState,
    Variety,
    VarietyParamRow,
)
from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.settings import settings


# --- Datos de Tabla Base (imagen1.csv) ---
_BASE_ROWS = [
    BaseTableRow(
        project_name="1. Trujillo",
        unit="tn",
        values={
            "T2627": 37, "T2728": 38, "T2829": 39,
            "T2930": 40, "T3031": 41, "T3132": 42,
        },
        total=237,
    ),
    BaseTableRow(
        project_name="2. Olmos",
        unit="tn",
        values={
            "T2627": 8, "T2728": 8, "T2829": 8,
            "T2930": 8, "T3031": 8, "T3132": 8,
        },
        total=48,
    ),
    BaseTableRow(
        project_name="3. Productores Terceros",
        unit="tn",
        values={
            "T2627": 14, "T2728": 15, "T2829": 15,
            "T2930": 15, "T3031": 15, "T3132": 15,
        },
        total=89,
    ),
]

# Variación definida por usuario (imagen1.csv fila 7; T2627 sin valor = 0)
_BASE_VARIATION = {
    "T2627": 0.0,
    "T2728": -7.0,
    "T2829": -7.0,
    "T2930": -7.0,
    "T3031": -7.0,
    "T3132": -7.0,
}

# --- Variedad 1 (imagen2.csv) ---
_VARIETY_1_PARAMS = [
    # Año 1: productividad=2, densidad=6500, precio=4, recaudación=100%
    VarietyParamRow(plant_year=1, productividad=2.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=1.0),
    VarietyParamRow(plant_year=2, productividad=3.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=1.0),
    VarietyParamRow(plant_year=3, productividad=4.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=0.9),
    VarietyParamRow(plant_year=4, productividad=5.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=0.8),
    VarietyParamRow(plant_year=5, productividad=5.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=0.7),
    VarietyParamRow(plant_year=6, productividad=5.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=0.6),
    VarietyParamRow(plant_year=7, productividad=5.0, densidad=6500.0, precio_estimado=4.0, pct_recaudacion=0.6),
]

# --- Reglas default (imagen5.csv) ---
_DEFAULT_RULES = Rules(
    royaltie_fob=0.12,
    costo_plantines=3.5,
    interes_financiamiento=0.0,
    financiamiento_anios=5,
)

# --- Nuevos Proyectos (imagen6.csv) ---
# Crecimiento Hortifrut: CHAO=250 ha T2627, OLMOS=200 ha T2728
# Recambio Varietal: OLMOS=50 ha T2627
# Nuevos Prod Terceros: Talsa=100 ha T2627 + 100 ha T2728, Diamond Bridge=25 ha T2627
_NEW_PROJECT_CELLS = [
    # 1. Crecimiento Hortifrut
    NewProjectCell(
        bloque=BloqueKind.CRECIMIENTO_HF, sub_proyecto="CHAO",
        variety_name="Variedad 1", season="T2627", hectareas=250,
    ),
    NewProjectCell(
        bloque=BloqueKind.CRECIMIENTO_HF, sub_proyecto="OLMOS",
        variety_name="Variedad 1", season="T2728", hectareas=200,
    ),
    # 2. Recambio Varietal
    NewProjectCell(
        bloque=BloqueKind.RECAMBIO_VARIETAL, sub_proyecto="OLMOS",
        variety_name="Variedad 1", season="T2627", hectareas=50,
    ),
    # 3. Nuevos Prod Terceros
    NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS, sub_proyecto="Talsa",
        variety_name="Variedad 1", season="T2627", hectareas=100,
    ),
    NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS, sub_proyecto="Talsa",
        variety_name="Variedad 1", season="T2728", hectareas=100,
    ),
    NewProjectCell(
        bloque=BloqueKind.NUEVOS_TERCEROS, sub_proyecto="Diamond Bridge",
        variety_name="Variedad 1", season="T2627", hectareas=25,
    ),
]


def _build_reference_state() -> ScenarioState:
    """
    Construye el ScenarioState completo de referencia basado en imagen1-6.csv.

    Returns:
        ScenarioState: Estado completo listo para persistir con ScenarioRepo.create().
    """
    return ScenarioState(
        name="Escenario Base - Perú 2026",
        country="Perú",
        base_table=BaseTable(
            rows=_BASE_ROWS,
            variation=_BASE_VARIATION,
        ),
        varieties=[
            Variety(name="Variedad 1", params=_VARIETY_1_PARAMS),
        ],
        rules=_DEFAULT_RULES,
        new_project_cells=_NEW_PROJECT_CELLS,
    )


def _delete_all_scenarios(session: Session) -> None:
    """
    Elimina todos los escenarios de la base de datos en orden correcto de FK.

    Ejecuta DELETE SQL en el orden inverso de dependencias para evitar
    violaciones de FK cuando el cascade ORM no está configurado en los modelos.

    Args:
        session: Sesión activa de SQLAlchemy.
    """
    from sqlalchemy import text

    # Orden de eliminación: hijos primero, padres después
    delete_order = [
        "new_project_ha",
        "new_project_subrow",
        "new_project_group",
        "variety_param",
        "variety",
        "rules",
        "base_table_value",
        "base_table_row",
        "base_table_variation",
        "season",
        "scenario",
    ]
    for table in delete_order:
        session.execute(text(f"DELETE FROM {table}"))
        print(f"  Tabla '{table}' limpiada.")
    session.commit()


def seed_db(force: bool = True) -> None:
    """
    Puebla la base de datos con el escenario de referencia oficial.

    Replica exactamente los datos de docs/image/imagen1-6.csv para que la UI
    muestre los valores del plan de negocio HF Perú al iniciar por primera vez.

    Args:
        force (bool): Si True, elimina escenarios previos antes de insertar.
            Usar con cuidado en producción. Por defecto True en scripts de setup.
    """
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        repo = ScenarioRepo(session)

        if force:
            print("Eliminando escenarios anteriores...")
            # Usar delete SQL raw en orden de FK en lugar del ORM delete
            _delete_all_scenarios(session)

        print("Creando escenario de referencia (imagen1-6.csv)...")
        state = _build_reference_state()
        scenario_id = repo.create(state)
        session.commit()
        print(f"[OK] Escenario creado con ID: {scenario_id}")

        # Validacion rapida: recargar desde DB para confirmar integridad
        loaded = repo.get(scenario_id)
        assert loaded is not None, "Error: ScenarioRepo.get() devolvio None tras creacion"
        assert len(loaded.varieties) == 1, f"Error: esperaba 1 variedad, encontre {len(loaded.varieties)}"
        assert len(loaded.varieties[0].params) == 7, "Error: la variedad debe tener 7 annos"
        assert len(loaded.base_table.rows) == 3, "Error: la tabla base debe tener 3 proyectos"
        print(f"[OK] Validacion: {len(loaded.varieties)} variedad(es), {len(loaded.base_table.rows)} filas de Tabla Base")

    engine.dispose()
    print("Seed completado exitosamente.")


if __name__ == "__main__":
    seed_db()
