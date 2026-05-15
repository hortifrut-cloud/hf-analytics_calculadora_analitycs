"""Inicializa var/app.db con el escenario canónico de UI.png.

Uso:  uv run python scripts/seed_dev_db.py
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
