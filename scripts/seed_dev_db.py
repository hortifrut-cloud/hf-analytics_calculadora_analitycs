"""
Archivo: seed_dev_db.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Script de utilidad para inicializar la base de datos de desarrollo (SQLite) 
con un escenario canónico basado en el diseño UI.png. Automatiza la 
creación de tablas y la inserción de datos de prueba para asegurar un 
entorno de desarrollo consistente.

Acciones Principales:
    - Creación del directorio de datos `var/`.
    - Inicialización de tablas mediante SQLAlchemy `create_all`.
    - Inserción de semillas (seeds) para escenarios, variedades y reglas.

Estructura Interna:
    - Bloque `if __name__ == "__main__":`: Orquesta el proceso de inicialización.

Ejecución:
    uv run python scripts/seed_dev_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.seeds import seed_ui_png
from backend.db.session import make_engine, make_session_factory
from backend.settings import settings

if __name__ == "__main__":
    Path("var").mkdir(exist_ok=True)
    engine = make_engine(settings.database_url)

    # Crea tablas si no existen (sin Alembic — solo para dev rápido)
    from backend.db.base import Base
    import backend.db.models  # noqa: F401

    Base.metadata.create_all(engine)

    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        scenario_id = seed_ui_png(session)
        print(f"Escenario canónico creado con ID={scenario_id}")
