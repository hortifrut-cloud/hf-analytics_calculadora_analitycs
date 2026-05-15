"""Fixtures E2E para Playwright.

Levanta un uvicorn real con una SQLite efímera sembrada con el escenario
canónico de UI.png.  Cada función de test recibe un `page` fresco pero
comparte el servidor (scope="session") para mayor velocidad.
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
