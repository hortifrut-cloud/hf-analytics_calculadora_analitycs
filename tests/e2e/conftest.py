"""
Archivo: conftest.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Orquestador de fixtures para pruebas de extremo a extremo (E2E) utilizando 
Playwright. Gestiona el ciclo de vida de un servidor Uvicorn real y una 
base de datos SQLite efímera sembrada con datos canónicos, permitiendo 
validar la integración completa entre el frontend Astro y el backend Shiny.

Acciones Principales:
    - Gestión de puerto dinámico para el servidor de pruebas.
    - Inicialización y sembrado de base de datos temporal para aislamiento.
    - Lanzamiento y terminación de procesos de servidor asíncronos.
    - Provisión de objetos `page` de Playwright configurados con el servidor vivo.

Estructura Interna:
    - `live_server`: Fixture de sesión que levanta la infraestructura.
    - `page`: Fixture de función que entrega un contexto de navegación limpio.
    - `_seed_temp_db`: Helper para preparar el estado inicial de la DB.

Ejecución:
    Invocado automáticamente por pytest en el directorio tests/e2e/.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _seed_temp_db(db_url: str) -> None:
    """Siembra la DB efímera con el escenario canónico de UI.png."""
    sys.path.insert(0, str(ROOT))

    import backend.db.models  # noqa: F401 — registra todos los modelos

    from backend.db.base import Base
    from backend.db.seeds import seed_ui_png
    from backend.db.session import make_engine, make_session_factory

    engine = make_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        seed_ui_png(session)
    engine.dispose()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def live_server() -> Generator[str, None, None]:
    """Levanta uvicorn con SQLite efímera semilla; devuelve la base URL."""
    port = _free_port()
    db_dir = tempfile.mkdtemp(prefix="hf_e2e_")
    db_path = Path(db_dir) / "e2e.db"
    db_url = f"sqlite:///{db_path}"

    _seed_temp_db(db_url)

    env = {**os.environ, "DATABASE_URL": db_url}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
            "--log-level",
            "warning",
        ],
        env=env,
        cwd=str(ROOT),
    )

    base_url = f"http://127.0.0.1:{port}"

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{base_url}/api/status", timeout=2)
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("uvicorn terminó antes de estar listo")
            time.sleep(0.5)
    else:
        proc.terminate()
        raise TimeoutError("El servidor no arrancó en 30 s")

    yield base_url

    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def _playwright() -> Generator[Playwright, None, None]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def _browser(_playwright: Playwright) -> Generator[Browser, None, None]:
    browser = _playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def page(_browser: Browser, live_server: str) -> Generator[Page, None, None]:
    """Contexto de browser fresco por test; base URL = live_server."""
    ctx: BrowserContext = _browser.new_context(base_url=live_server)
    p = ctx.new_page()
    yield p
    ctx.close()
