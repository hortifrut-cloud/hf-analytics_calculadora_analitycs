"""
Archivo: session.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Factoría de motores y sesiones de base de datos. Implementa una lógica dual 
para soportar SQLite (desarrollo/tests) y PostgreSQL/Supabase (producción).

Acciones Principales:
    - Creación de Engine con configuraciones específicas de pooling.
    - Manejo de sesiones in-memory para entornos de test.
    - Optimización de conexiones para el transaction pooler de Supabase.

Estructura Interna:
    - `make_engine`: Configura el motor SQLAlchemy según la URL de conexión.
    - `make_session_factory`: Crea la factoría de sesiones con parámetros optimizados.

Ejemplo de Integración:
    from backend.db.session import make_engine, make_session_factory
    engine = make_engine(DATABASE_URL)
    SessionFactory = make_session_factory(engine)
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool


def make_engine(url: str) -> Engine:
    """
    Crea un motor de SQLAlchemy adaptado al tipo de base de datos y entorno.

    Args:
        url (str): URL de conexión a la base de datos.

    Returns:
        Engine: Instancia del motor configurada.
    """
    if "pooler.supabase.com" in url:
        return create_engine(url, poolclass=NullPool, future=True)
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}, "future": True}
        if ":memory:" in url:
            # StaticPool asegura que todas las conexiones comparten
            # la misma DB in-memory (necesario para tests con hilos).
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Crea una factoría de sesiones configurada para el motor proporcionado.

    Args:
        engine (Engine): Motor de base de datos previamente creado.

    Returns:
        sessionmaker[Session]: Factoría para generar nuevas sesiones de base de datos.
    """
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
