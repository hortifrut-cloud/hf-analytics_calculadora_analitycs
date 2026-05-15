"""Tests integración — T3.2: modelos ORM y restricciones."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from backend.db.base import Base
from backend.db.models import Scenario, Season, Variety, VarietyParam, Rules, AuditLog
from backend.db.session import make_engine, make_session_factory

import backend.db.models as _all_models  # noqa: F401 — registra todos los modelos


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


def test_all_tables_created(engine):
    expected = {
        "scenario",
        "season",
        "base_table_row",
        "base_table_value",
        "base_table_variation",
        "variety",
        "variety_param",
        "rules",
        "new_project_group",
        "new_project_subrow",
        "new_project_ha",
        "audit_log",
    }
    actual = set(inspect(engine).get_table_names())
    assert expected.issubset(actual)


def test_scenario_create(session):
    sc = Scenario(name="Test")
    session.add(sc)
    session.flush()
    assert sc.id is not None


def test_variety_param_unique_constraint(session):
    sc = Scenario(name="S")
    session.add(sc)
    session.flush()
    v = Variety(scenario_id=sc.id, name="V1")
    session.add(v)
    session.flush()
    session.add(
        VarietyParam(
            variety_id=v.id,
            plant_year=1,
            productividad=2.0,
            densidad=6500,
            precio_estimado=4.0,
            pct_recaudacion=1.0,
        )
    )
    session.flush()
    # Duplicate plant_year → IntegrityError
    with pytest.raises(IntegrityError):
        session.add(
            VarietyParam(
                variety_id=v.id,
                plant_year=1,
                productividad=3.0,
                densidad=6500,
                precio_estimado=4.0,
                pct_recaudacion=1.0,
            )
        )
        session.flush()


def test_rules_1to1_per_scenario(session):
    sc = Scenario(name="S2")
    session.add(sc)
    session.flush()
    session.add(Rules(scenario_id=sc.id))
    session.flush()
    with pytest.raises(IntegrityError):
        session.add(Rules(scenario_id=sc.id))
        session.flush()


def test_audit_log_json_payload(session):
    sc = Scenario(name="S3")
    session.add(sc)
    session.flush()
    payload = {"action": "update", "old": 5, "new": 3}
    log = AuditLog(scenario_id=sc.id, entity="rules", payload=payload)
    session.add(log)
    session.flush()
    session.expire(log)
    loaded = session.get(AuditLog, log.id)
    assert loaded.payload == payload
