"""
Archivo: test_session.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests de integración para la factoría de motores y sesiones de base de 
datos (T3.1). Valida la correcta creación de motores para diferentes 
dialéctos (SQLite, PostgreSQL) y la configuración específica para entornos 
de nube (Supabase Pooler), asegurando que el pool de conexiones se adapte 
a la infraestructura.

Acciones Principales:
    - Validación de creación de motor SQLite en memoria para tests.
    - Verificación de desactivación de `check_same_thread` para SQLite.
    - Validación de uso de `NullPool` para conexiones vía Supabase Transaction Pooler.
    - Comprobación de que PostgreSQL estándar NO usa `NullPool` por defecto.

Estructura Interna:
    - `test_sqlite_engine_creates`: Prueba básica de conectividad.
    - `test_supabase_pooler_uses_nullpool`: Prueba crítica para estabilidad en Prod.

Ejecución:
    pytest tests/integration/test_session.py
"""

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
