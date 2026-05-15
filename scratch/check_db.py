"""
Archivo: check_db.py
Fecha de modificación: 15/05/2026
Autor: Antigravity

Descripción:
Script de utilidad para verificar la existencia de escenarios en la base de datos
utilizando la configuración de sesión del proyecto.

Acciones Principales:
    - Conexión a la base de datos configurada en .env.
    - Conteo y listado de escenarios.

Ejecución:
    python check_db.py
"""

from backend.db.session import make_engine, make_session_factory
from backend.db.models import Scenario
from backend.settings import settings
from sqlalchemy import select

def check_db() -> None:
    """Consulta la tabla de escenarios y muestra los resultados en consola."""
    engine = make_engine(settings.database_url)
    SessionFactory = make_session_factory(engine)
    with SessionFactory() as session:
        scenarios = session.execute(select(Scenario)).scalars().all()
        print(f"Total scenarios: {len(scenarios)}")
        for s in scenarios:
            print(f"- ID: {s.id}, Name: {s.name}")
    engine.dispose()

if __name__ == "__main__":
    check_db()
