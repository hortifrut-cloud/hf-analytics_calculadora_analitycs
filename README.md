# HF Breeding Planner — Business Planning 2026

Simulador de planificación de negocio para el área de blueberries de **Hortifrut Perú**, temporadas T26/27 → T31/32. Permite modelar escenarios de crecimiento, recambio varietal y proyectos con terceros, con recálculo automático de producción y ganancia consolidada en tiempo real.

> Descripción funcional completa y fórmulas → [`docs/description_proyecto.md`](docs/description_proyecto.md)

---

## Stack

| Capa | Tecnología | Rol |
|---|---|---|
| Frontend | Astro 4 + Tailwind CSS | Shell SPA estático, embebe Shiny via iframe |
| Servidor | Starlette (ASGI) | Router único: API REST + Shiny + estáticos |
| Dashboard | Shiny for Python ≥ 1.2 | UI reactiva con debounce 1.5 s y caché en memoria |
| Cálculo | Pandas ≥ 2.2 · NumPy ≥ 2.1 | Motor puro sin I/O, pipeline topológico determinístico |
| ORM | SQLAlchemy 2.x + Alembic | Modelos + migraciones, compatible SQLite y Postgres |
| Base de datos | SQLite (dev) · Supabase Postgres (prod) | Mismo código ORM en ambos entornos |
| Deploy | ShinyApps.io + rsconnect-python | Un comando para redeploy |

> Stack completo con justificaciones → [`docs/plan/plan_maestro.md`](docs/plan/plan_maestro.md)

---

## Quick start

```powershell
# 1. Instalar dependencias
uv sync
cd frontend && pnpm install && cd ..

# 2. Configurar entorno
Copy-Item .env.example .env   # editar DATABASE_URL si se usa Supabase

# 3. Sembrar base de datos y arrancar
uv run python scripts/seed_dev_db.py
.\scripts\dev.ps1
```

| Servicio | URL |
|---|---|
| App completa (Starlette) | http://localhost:8000 |
| Dashboard Shiny | http://localhost:8000/shiny/ |
| Frontend Astro (dev HMR) | http://localhost:4321 |
| API health check | http://localhost:8000/api/status |

---

## Tests

```powershell
uv run python -m pytest tests/unit -v        # lógica pura
uv run python -m pytest tests/golden -v      # vs. CSVs de referencia docs/image/
uv run python -m pytest tests/integration -v # API + DB SQLite en memoria
uv run python -m pytest tests/property -v    # invariantes Hypothesis (200 ejemplos)
uv run python -m pytest tests/e2e -v         # Playwright headless (auto-levanta servidor)
uv run python -m pytest -v                   # suite completa
```

---

## Build y despliegue

```powershell
# Compilar frontend y copiar estáticos
.\scripts\build.ps1

# Verificar build localmente
uv run python -m uvicorn app:app --port 8000

# Deploy a ShinyApps.io
# (ver ejecucion.md §5 para configurar credenciales rsconnect)
```

> Guía completa de instalación, build y despliegue → [`ejecucion.md`](ejecucion.md)

---

## Estructura del repositorio

```
hf-breeding-planner/
├── app.py                      # Entrypoint Starlette (ShinyApps.io: app:app)
├── backend/
│   ├── domain/                 # Modelos Pydantic inmutables (ScenarioState, DerivedState)
│   ├── logic/                  # Motor de cálculo puro — sin I/O, sin efectos secundarios
│   ├── db/                     # ORM SQLAlchemy, repositorios, seeds, Alembic
│   ├── api/                    # Endpoints REST Starlette
│   └── shiny_app/              # App Shiny + módulos UI + bridge state.py
├── frontend/                   # Shell Astro SPA (se compila a backend/static/)
├── tests/
│   ├── unit/                   # Tests de lógica pura
│   ├── golden/                 # Tests contra docs/image/*.csv
│   ├── integration/            # API + DB in-memory
│   ├── property/               # Hypothesis: no-negatividad, idempotencia, monotonía
│   └── e2e/                    # Playwright: flujo completo UI.png
├── scripts/                    # dev.ps1, build.ps1, inline_js.py, seed_dev_db.py
└── docs/
    ├── architect/              # Diagramas de arquitectura (visión ejecutiva)
    ├── plan/                   # Plan maestro de implementación
    ├── image/                  # CSVs y PNGs de referencia (golden data)
    └── task/                   # Backlog de tareas por fase
```

---

## Documentación

| Documento | Audiencia | Contenido |
|---|---|---|
| [`docs/architect/architecture.md`](docs/architect/architecture.md) | Ejecutivos / Arquitectos | Diagramas C4, flujo reactivo, deployment |
| [`docs/documentation.md`](docs/documentation.md) | Tech leads / Developers | Referencia técnica profunda, debugging guide |
| [`docs/description_proyecto.md`](docs/description_proyecto.md) | Product / Dev | Especificación funcional y fórmulas de negocio |
| [`ejecucion.md`](ejecucion.md) | DevOps / Dev | Build, deploy, troubleshooting |
| [`CLAUDE.md`](CLAUDE.md) | Agente IA | Comandos, arquitectura, gotchas |

---

> Uso interno — Hortifrut Chile S.A.
