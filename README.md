# HF Breeding Planner — Business Planning 2026

Plataforma analítica interactiva para simular escenarios del plan de breeding de arándanos (Hortifrut Perú).

> Descripción funcional completa → [`docs/description_proyecto.md`](docs/description_proyecto.md)

---

## Qué hace

El usuario confirma un escenario financiero macro, define variedades con parámetros agronómicos por año de plantación, edita hectáreas planificadas por temporada y proyecto, y observa cómo se recalculan dinámicamente (debounce 1.5 s) los sub-totales y totales consolidados Hortifrut vs. Terceros. Todo el estado persiste en base de datos y sobrevive recargas.

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Shell estático | Astro 4 + Tailwind CSS |
| API / ASGI host | Starlette |
| Dashboard reactivo | Shiny for Python ≥ 1.2 |
| Cálculo | Pandas ≥ 2.2 + NumPy ≥ 2.1 |
| ORM / Migraciones | SQLAlchemy 2.x + Alembic |
| DB dev | SQLite (`var/app.db`) |
| DB cloud | Supabase Postgres (transaction pooler) |
| Gestor Python | uv |
| Gestor Node | pnpm |
| Tests | pytest + Hypothesis + Playwright |

> Stack completo con justificaciones → [`docs/plan/plan_maestro.md §Stack`](docs/plan/plan_maestro.md)

---

## Quick start

```powershell
# 1. Instalar dependencias Python
uv sync

# 2. Configurar variables de entorno
Copy-Item .env.example .env   # editar DATABASE_URL si es necesario

# 3. Levantar backend + frontend en paralelo
.\scripts\dev.ps1
```

- **Backend + Shiny**: http://localhost:8000/shiny/
- **API status**: http://localhost:8000/api/status
- **Frontend Astro dev**: http://localhost:4321

> Guía detallada de instalación y despliegue → [`ejecucion.md`](ejecucion.md)

---

## Tests

```powershell
# Tests unitarios y golden
uv run python -m pytest tests/unit tests/golden -v

# Tests de integración (API + DB)
uv run python -m pytest tests/integration -v

# Tests E2E con Playwright (levanta servidor interno automáticamente)
uv run python -m pytest tests/e2e -v

# Suite completa
uv run python -m pytest -v
```

---

## Build para producción

```powershell
.\scripts\build.ps1
```

Compila el frontend Astro, inyecta JS inline (compatibilidad ShinyApps.io) y copia estáticos a `backend/static/`. Luego verificar localmente:

```powershell
uv run python -m uvicorn app:app --port 8000
```

---

## Despliegue a ShinyApps.io

Ver [`ejecucion.md §5`](ejecucion.md#5-despliegue-en-shinyappsio).

---

## Estructura del repositorio

```
hf-breeding-planner/
├── app.py                  # Entrypoint Starlette (ShinyApps.io)
├── backend/
│   ├── domain/             # Modelos Pydantic (ScenarioState, DerivedState)
│   ├── logic/              # Motor de cálculo puro (sin I/O)
│   ├── db/                 # ORM, repos, seeds, Alembic
│   ├── api/                # Endpoints REST
│   └── shiny_app/          # App Shiny + módulos UI
├── frontend/               # Shell Astro (SPA estática)
├── tests/
│   ├── unit/               # Tests de lógica pura
│   ├── golden/             # Tests contra docs/image/*.csv
│   ├── integration/        # API + DB
│   ├── property/           # Hypothesis (invariantes)
│   └── e2e/                # Playwright
├── scripts/                # dev.ps1, build.ps1, seed_dev_db.py
└── docs/                   # Especificaciones, plan, imágenes de referencia
```

---

## Licencia

Uso interno — Hortifrut Chile S.A.
