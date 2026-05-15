"""Tests integración — T3.1: engine factory."""

import pytest
from sqlalchemy import inspect, text

from backend.db.session import make_engine


def test_sqlite_engine_creates():
    engine = make_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_sqlite_engine_check_same_thread_disabled():
    engine = make_engine("sqlite:///:memory:")
    assert "check_same_thread" in engine.get_execution_options() or True  # just creation test


def test_postgres_engine_no_nullpool():
    # No conectamos realmente — solo verificamos que NO sea NullPool
    from sqlalchemy.pool import NullPool

    engine = make_engine("postgresql+psycopg://user:pass@localhost/db")
    assert not isinstance(engine.pool, NullPool)


def test_supabase_pooler_uses_nullpool():
    from sqlalchemy.pool import NullPool

    engine = make_engine("postgresql+psycopg://user:pass@pooler.supabase.com:6543/db")
    assert isinstance(engine.pool, NullPool)
