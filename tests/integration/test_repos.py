"""
Archivo: test_repos.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para la capa de Repositorios (T3.5). Valida el flujo 
"round-trip" de los objetos de dominio (ScenarioState, Rules) a través de 
los repositorios hacia la base de datos y su recuperación posterior, 
asegurando que no haya pérdida de fidelidad en la persistencia.

Acciones Principales:
    - Validación del ciclo de vida completo de un escenario (Create, Get, Delete).
    - Verificación de la recuperación correcta de celdas de hectáreas.
    - Prueba de actualización de reglas de negocio globales.
    - Validación de registro de eventos en el log de auditoría.

Estructura Interna:
    - `test_scenario_roundtrip`: Prueba principal de persistencia de dominio.
    - `test_rules_get_update`: Validación de edición de reglas.
    - `test_audit_log`: Validación de trazabilidad de cambios.

Ejecución:
    pytest tests/integration/test_repos.py
"""

import pytest

from backend.db.base import Base
from backend.db.repos import AuditRepo, RulesRepo, ScenarioRepo
from backend.db.seeds import build_ui_png_scenario
from backend.db.session import make_engine, make_session_factory
from backend.domain.inputs import Rules

import backend.db.models as _all_models  # noqa: F401


@pytest.fixture(scope="module")
def engine():
    eng = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        yield s
        s.rollback()


def test_scenario_roundtrip(session):
    """Crear ScenarioState → DB → recuperar → comparar."""
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)
    assert sid > 0

    recovered = repo.get(sid)
    assert recovered is not None
    assert recovered.name == original.name
    assert len(recovered.varieties) == len(original.varieties)
    # Variedades: mismos nombres
    orig_names = {v.name for v in original.varieties}
    recov_names = {v.name for v in recovered.varieties}
    assert orig_names == recov_names
    # Params: mismos plant_years
    for orig_v in original.varieties:
        rec_v = next(v for v in recovered.varieties if v.name == orig_v.name)
        orig_years = {p.plant_year for p in orig_v.params}
        rec_years = {p.plant_year for p in rec_v.params}
        assert orig_years == rec_years


def test_scenario_list_ids(session):
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)
    ids = repo.list_ids()
    assert any(s[0] == sid for s in ids)


def test_scenario_delete(session):
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)
    assert repo.delete(sid) is True
    assert repo.get(sid) is None
    assert repo.delete(sid) is False


def test_rules_cells_recovered(session):
    """Las celdas de ha no-cero se recuperan correctamente."""
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)
    recovered = repo.get(sid)
    orig_ha = {
        (c.bloque, c.sub_proyecto, c.season): c.hectareas for c in original.new_project_cells
    }
    rec_ha = {
        (c.bloque, c.sub_proyecto, c.season): c.hectareas for c in recovered.new_project_cells
    }
    assert orig_ha == rec_ha


def test_rules_get_update(session):
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)

    rules_repo = RulesRepo(session)
    rules = rules_repo.get(sid)
    assert rules is not None
    assert rules.royaltie_fob == pytest.approx(0.12)

    new_rules = Rules(
        royaltie_fob=0.15, costo_plantines=4.0, interes_financiamiento=0.0, financiamiento_anios=3
    )
    rules_repo.update(sid, new_rules)
    updated = rules_repo.get(sid)
    assert updated.royaltie_fob == pytest.approx(0.15)
    assert updated.financiamiento_anios == 3


def test_audit_log(session):
    original = build_ui_png_scenario()
    repo = ScenarioRepo(session)
    sid = repo.create(original)

    audit = AuditRepo(session)
    audit.log(
        entity="rules", payload={"change": "financiamiento", "old": 5, "new": 3}, scenario_id=sid
    )
    session.commit()

    from backend.db.models import AuditLog

    logs = session.query(AuditLog).filter_by(scenario_id=sid, entity="rules").all()
    assert len(logs) >= 1
    assert logs[-1].payload["change"] == "financiamiento"
