"""Engine factory dual: SQLite (dev) o Postgres/Supabase (cloud).

Supabase transaction pooler (pooler.supabase.com) ya hace connection pooling
vía Supavisor — usar NullPool evita doble pooling que causa conexiones colgadas.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool


def make_engine(url: str) -> Engine:
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
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
