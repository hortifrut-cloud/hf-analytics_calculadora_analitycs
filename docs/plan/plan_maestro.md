# Plan Maestro de Implementación

## Plataforma Business Planning — Plan Breeding Arándanos (Hortifrut Perú)

> **Propósito.** Guía exhaustiva por **Fases → Tareas** para construir la plataforma definida en [`docs/description_proyecto.md`](../description_proyecto.md). El backend se construye y prueba **antes** del frontend, con golden tests basados en los CSVs de `docs/image/` como verdad de referencia. La arquitectura sigue el patrón “Agro-Stack” validado en [`docs/plan_replication.md`](../plan_replication.md): **Astro (SPA) + Starlette (API + ASGI host) + Shiny for Python (dashboard reactivo)**, desplegable en **ShinyApps.io**.
>
> **Persistencia:** **SQLite** en dev y **Supabase Postgres** en cloud, ambos vía SQLAlchemy 2.x + Alembic.
>
> **Tooling:** **`uv`** para Python y **`pnpm`** para Node.
>
> **Cómo leer este documento.** Cada Fase resuelve un macro-problema; cada Tarea (`T{F}.{N}`) tiene **entregable**, **criterio de aceptación** verificable, **archivos involucrados** y **referencias a `description_proyecto.md`**. Este archivo será la fuente para generar el listado granular de tareas en una iteración posterior.

---

## Índice

- [Convenciones y nomenclatura](#convenciones-y-nomenclatura)
- [Stack tecnológico definitivo](#stack-tecnológico-definitivo)
- [Estructura objetivo del repositorio](#estructura-objetivo-del-repositorio)
- [Datos de referencia (fixtures)](#datos-de-referencia-fixtures)
- **Fase 0** — Setup del repositorio y herramientas
- **Fase 1** — Modelo de dominio puro (sin DB, sin UI)
- **Fase 2** — Motor de cálculo + golden tests con CSVs reales
- **Fase 3** — Persistencia: SQLAlchemy + SQLite dev + Supabase
- **Fase 4** — API Starlette (CRUD + recompute + export)
- **Fase 5** — Aplicación Shiny (UI reactiva con debounce)
- **Fase 6** — Integración Starlette ↔ Shiny ↔ estáticos
- **Fase 7** — Frontend Astro (shell SPA + iframe)
- **Fase 8** — Tests E2E con Playwright
- **Fase 9** — Documentación (`README.md` raíz + `ejecucion.md`)
- **Fase 10** — Despliegue (Supabase + ShinyApps.io)

---

## Convenciones y nomenclatura

- **Variedad V**, **Temporada t** (códigos `T2627..T3132`), **Año de planta n ∈ {1..7}**.
- **Bloques** de Nuevos Proyectos: `crecimiento_hf` (B1), `recambio_varietal` (B2), `nuevos_terceros` (B3).
- **Sub-proyectos**: B1/B2 → `CHAO`, `OLMOS`. B3 → `Talsa`, `Diamond Bridge` (todos extensibles desde DB).
- **Productores** en `[Tabla cálculos variedades]`: `hf_interna`, `hf_terceros`, `terceros`.
- **Identificadores Python**: `snake_case`. **Tablas SQL**: `snake_case` singular. **Módulos `/logic`**: un archivo por bloque/concepto.
- **Idempotencia**: cualquier función de `/logic` debe ser pura — mismo input ⇒ mismo output, sin I/O.
- **Unidades**: ha, Kg/planta, planta/ha, FOB/kg, FOB/ha. Conversión a tn / miles $ **solo al final del cálculo** (factor `/1000`).
- **Debounce global**: `DEBOUNCE_MS = 1500` (configurable en `.env`).
- **Comentarios en código**: solo el “por qué” cuando no es obvio. Sin docstrings extensos.

---

## Stack tecnológico definitivo

| Capa                            | Tecnología                                              | Versión sugerida | Justificación / Notas (validado con Context7)                                                                                            |
| ------------------------------- | ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Lenguaje backend                | **Python**                                              | ≥ 3.11           | Si se va a 3.13, fijar `numpy >= 2.1.0` (sin wheels < 2.1 en 3.13, ver `plan_replication.md` §4.1).                                       |
| Gestor de paquetes Python       | **uv**                                                  | latest           | 10–100× más rápido que `pip`. Determinismo con `uv.lock`.                                                                                |
| API HTTP / ASGI host            | **Starlette**                                           | ≥ 0.45           | Ultraligero, asíncrono, **compatible nativo con ShinyApps.io** (FastAPI no se soporta en ese entorno).                                  |
| Dashboard reactivo              | **Shiny for Python**                                    | ≥ 1.2            | `@reactive.calc`, `@reactive.event`, `reactive.extended_task` y `reactive.invalidate_later` cubren memoización, eventos y debounce.     |
| Cálculo                         | **Pandas + NumPy**                                      | ≥ 2.2 / ≥ 2.1    | `DataFrame.shift(periods=n, axis=1)` para lags fenológicos.                                                                              |
| ORM                             | **SQLAlchemy 2.x** (`Mapped[...]`)                      | ≥ 2.0.36         | Misma base de código para SQLite ↔ Postgres.                                                                                             |
| Migraciones                     | **Alembic**                                             | ≥ 1.13           | Evitar tipos exclusivos de Postgres (`JSONB` → `JSON`; usar `Integer` autoincrement en lugar de `SERIAL`).                              |
| DB (dev)                        | **SQLite** (archivo `var/app.db`)                       | ≥ 3.40           | Cero infraestructura; commit del seed, no del `.db`.                                                                                     |
| DB (cloud)                      | **Supabase Postgres** (transaction pooler, port `6543`) | -                | Free tier 500 MB. Conectar con **`NullPool` de SQLAlchemy** para no duplicar pooling sobre Supavisor (ver §Despliegue).                  |
| Frontend shell                  | **Astro** (SPA, `output: 'static'`)                     | ≥ 4              | `inlineStylesheets: 'always'` para evitar rutas `/_astro/` rotas en ShinyApps.io.                                                        |
| Gestor de paquetes Node         | **pnpm** (via `corepack enable`)                        | latest           | Evita *phantom deps*; lockfile determinista.                                                                                             |
| Styling                         | **Tailwind CSS**                                        | latest           | Tokens para colores `ciruela` (`#E7B6D1`) y `verde` (`#0E7C3E`).                                                                         |
| Testing — unit                  | **pytest** + **Hypothesis**                             | latest           | Property-based para invariantes del motor (no-negatividad, monotonía).                                                                   |
| Testing — E2E                   | **Playwright (Python)**                                 | latest           | Reproduce el flujo del usuario en la UI Shiny.                                                                                           |
| Linter / formatter              | **ruff** + **black**                                    | latest           | Pre-commit hooks; reglas estrictas (E, F, I, B, UP).                                                                                     |
| Type checker                    | **mypy** (estricto) o **pyright**                       | latest           | Modelos de dominio con `Mapped[...]` o Pydantic.                                                                                         |
| Validación de schemas           | **Pydantic v2**                                         | ≥ 2.6            | Para `ScenarioState` y payloads de API.                                                                                                  |
| Despliegue cloud (frontend+app) | **ShinyApps.io** + **`rsconnect-python`**               | -                | Mismo patrón del repo de referencia (`plan_replication.md`).                                                                             |
| Dev orchestration               | **Docker compose** + script `scripts/dev.ps1`           | -                | Levantar Postgres local opcional + app en un comando.                                                                                    |

---

## Estructura objetivo del repositorio

> Sigue el patrón validado en `plan_replication.md`. Las carpetas marcadas con `*` no se commitean (van a `.gitignore` y `.rscignore`).

```text
hf-breeding-planner/
│
├── app.py                       # Entrypoint Starlette para ShinyApps.io
├── pyproject.toml               # uv project + dependencias Python
├── uv.lock                      # Lockfile uv (commitear)
├── requirements.txt             # Generado con `uv pip compile` para rsconnect
├── alembic.ini                  # Config Alembic
├── .python-version              # 3.11+ (o 3.13)
├── .env                         # NO commitear *
├── .env.example                 # Plantilla (commitear)
├── .gitignore
├── .rscignore                   # Exclusiones para ShinyApps.io
├── docker-compose.yml           # Postgres local opcional
│
├── backend/
│   ├── __init__.py
│   ├── settings.py              # Pydantic Settings: DATABASE_URL, DEBOUNCE_MS, ...
│   ├── main.py                  # Dev server FastAPI/uvicorn (NO usado en prod)
│   ├── dashboard.py             # Punto de entrada Shiny (re-exporta `backend.shiny_app.app`)
│   │
│   ├── domain/                  # Modelos puros (Pydantic) — sin DB, sin Shiny
│   │   ├── __init__.py
│   │   ├── enums.py             # Productor, BloqueKind, Unidad
│   │   ├── inputs.py            # ScenarioState, VarietyParams, Rules, NewProjectHa
│   │   └── derived.py           # DerivedState, CalculosVariedad, MatrizSubyacente
│   │
│   ├── logic/                   # Motor de cálculo — PURO, sin I/O
│   │   ├── __init__.py
│   │   ├── calculos_variedades.py   # §3.4
│   │   ├── lag_matrix.py            # §3.5 — helpers de shift temporal
│   │   ├── crecimiento_hf.py        # §3.6
│   │   ├── recambio.py              # §3.7
│   │   ├── nuevos_terceros.py       # §3.8.1
│   │   ├── plantines.py             # §3.8.2 (truncamiento por Financiamiento)
│   │   ├── terceros_totales.py      # §3.9 (alimentado solo por B3)
│   │   ├── totales.py               # §3.10
│   │   └── recompute.py             # Orquestador: ScenarioState → DerivedState
│   │
│   ├── db/                      # Persistencia
│   │   ├── __init__.py
│   │   ├── base.py              # Declarative Base
│   │   ├── session.py           # Engine factory (SQLite/Postgres + NullPool en Supabase)
│   │   ├── models.py            # ORM (§1.3 description_proyecto)
│   │   ├── repos.py             # Repositorios: ScenarioRepo, VarietyRepo, ...
│   │   └── seeds.py             # Tabla Base default + Reglas default
│   │
│   ├── api/                     # Endpoints Starlette REST
│   │   ├── __init__.py
│   │   ├── routes.py            # Registro de rutas
│   │   ├── scenarios.py         # CRUD escenarios + Tabla Base
│   │   ├── varieties.py         # CRUD variedades + parámetros
│   │   ├── rules.py             # GET/PUT Reglas/Definiciones
│   │   ├── new_projects.py      # CRUD ha + recompute
│   │   └── exports.py           # /export/xlsx (xlsxwriter)
│   │
│   ├── shiny_app/               # UI Shiny por sección de UI.png
│   │   ├── __init__.py
│   │   ├── app.py               # `App(ui, server)` — entrypoint del módulo
│   │   ├── state.py             # Bridge: reactive.value(ScenarioState) ↔ API
│   │   ├── reactive_helpers.py  # debounce(input, ms) basado en invalidate_later
│   │   ├── styles.css           # Tokens visuales (ciruela / verde)
│   │   └── modules/
│   │       ├── base_table.py        # SECCIÓN 1 — Tabla Base
│   │       ├── varieties_panel.py   # SECCIÓN 2 — Datos Variedades
│   │       ├── rules_panel.py       # SECCIÓN 3 — Reglas / Definiciones
│   │       ├── new_projects.py      # SECCIÓN 4 — Nuevos Proyectos
│   │       └── totals.py            # SECCIÓN 5 — Totales
│   │
│   └── static/                  # Build Astro (generado, NO commitear) *
│
├── frontend/                    # Astro shell (SPA)
│   ├── astro.config.mjs         # output: 'static', inlineStylesheets: 'always'
│   ├── package.json
│   ├── pnpm-lock.yaml           # commitear
│   ├── tsconfig.json
│   ├── public/                  # favicon, og:image
│   └── src/
│       ├── pages/
│       │   └── index.astro      # Landing + <iframe src="./shiny/">
│       ├── components/
│       │   ├── Header.astro
│       │   └── ScenarioSwitcher.astro
│       └── styles/
│           └── tailwind.css     # tokens ciruela/verde
│
├── tests/
│   ├── conftest.py              # fixtures comunes
│   ├── fixtures/                # CSVs cargados desde docs/image/ a Python
│   │   └── README.md
│   ├── unit/
│   │   ├── test_calculos_variedades.py
│   │   ├── test_lag_matrix.py
│   │   ├── test_crecimiento_hf.py
│   │   ├── test_recambio.py
│   │   ├── test_nuevos_terceros.py
│   │   ├── test_plantines.py
│   │   ├── test_terceros_totales.py
│   │   └── test_totales.py
│   ├── golden/                  # Tests que comparan contra docs/image/imagen*.csv
│   │   ├── test_golden_imagen7_crecimiento.py
│   │   ├── test_golden_imagen8_recambio.py
│   │   ├── test_golden_imagen9_nuevos_terceros.py
│   │   ├── test_golden_imagen10_terceros_totales.py
│   │   └── test_golden_ui_totales.py
│   ├── property/
│   │   └── test_invariants.py   # Hypothesis: no-negatividad, monotonía, idempotencia
│   ├── integration/
│   │   ├── test_repos.py
│   │   ├── test_api_scenarios.py
│   │   ├── test_api_varieties.py
│   │   ├── test_api_new_projects.py
│   │   └── test_api_export.py
│   ├── simulation/
│   │   └── test_user_flow_ui_png.py   # Simula el flujo COMPLETO de UI.png
│   └── e2e/
│       └── test_playwright_flow.py
│
├── scripts/
│   ├── dev.ps1                  # Levanta backend + Astro dev en paralelo
│   ├── inline_js.py             # Post-procesador para ShinyApps.io
│   └── seed_dev_db.py           # Inicializa SQLite con datos de UI.png
│
├── alembic/
│   ├── env.py
│   └── versions/                # Migraciones generadas
│
└── docs/
    ├── description_proyecto.md
    ├── plan_replication.md
    ├── plan/
    │   └── plan_maestro.md      # ← este archivo
    ├── doc_guia/
    │   └── ejecucion.md         # plantilla de referencia
    ├── image/                   # imagen*.png + imagen*.csv (fixtures golden)
    └── README.md
```

---

## Datos de referencia (fixtures)

Todos los CSVs de `docs/image/imagen*.csv` se cargan tal cual como fixtures. El escenario canónico para tests proviene de `docs/image/UI.png` y los CSVs:

**Escenario canónico (V1):**

| Variable                 | Año 1 | Año 2 | Año 3 | Año 4 | Año 5 | Año 6 | Año 7 |
| ------------------------ | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Productividad (Kg/planta)| 2     | 3     | 4     | 5     | 5     | 5     | 5     |
| Densidad (planta/ha)     | 6500  | 6500  | 6500  | 6500  | 6500  | 6500  | 6500  |
| Precio estimado (FOB/kg) | 4     | 4     | 4     | 4     | 4     | 4     | 4     |
| % Recaudación            | 100%  | 100%  | 90%   | 80%   | 70%   | 60%   | 60%   |

Reglas: `Royaltie FOB = 12%`, `Costo Plantines = 3.5 $/planta`, `Interés = 0%`, `Financiamiento = 5 años`.

Hectáreas (UI.png, V1):

| Bloque                | Sub-proyecto    | T2627 | T2728 |
| --------------------- | --------------- | ----- | ----- |
| Crecimiento Hortifrut | CHAO            | 250   |       |
| Crecimiento Hortifrut | OLMOS           |       | 200   |
| Recambio varietal     | OLMOS           |       | 50    |
| Nuevos Prod Terceros  | Talsa           | 100   | 100   |
| Nuevos Prod Terceros  | Diamond Bridge  | 25    |       |

**Salidas esperadas (golden) — extraídas de UI.png e imagen 9:**

- B1 Subtotal producción T2728..T3132 (tn): `3,250 / 7,475 / 10,400 / 13,325 / 14,625`
- B1 Subtotal ganancia T2728..T3132 (miles $): `13,000 / 29,900 / 41,600 / 53,300 / 58,500`
- B2 Subtotal producción T2728..T3132 (tn): `650 / 975 / 1,300 / 1,625 / 1,625`
- B2 Subtotal ganancia T2728..T3132 (miles $): `2,600 / 3,900 / 5,200 / 6,500 / 6,500`
- B3 Subtotal producción T2728..T3132 (tn): `1,625 / 3,738 / 4,875 / 5,590 / 5,444`
- B3 Subtotal ganancia T2728..T3132 (miles $): `780 / 1,794 / 2,496 / 3,198 / 3,510`
- B3 Subtotal ganancia plantines T2728..T3132 (miles $): `569 / 1,024 / 1,024 / 1,024 / 1,024`
- Totales Hortifrut · Fruta T2728..T3132 (tn): `5,525 / 12,188 / 16,575 / 20,540 / 21,694`
- Totales Hortifrut · Ganancia T2728..T3132 (miles $): `16,949 / 36,618 / 50,320 / 64,022 / 69,534`
- Totales Terceros · Fruta T2728..T3132 (tn): `— / — / 325 / 1,073 / 1,869`
- Totales Terceros · Ganancia T2728..T3132 (miles $): `5,720 / 13,156 / 18,304 / 23,452 / 25,740`

**Tolerancia de comparación.** Los valores de UI.png están redondeados. Los tests deben:
- comparar **enteros** con `abs(diff) ≤ 1` para acomodar rounding bancario,
- comparar **floats** con `pytest.approx(rel=1e-3)`.

---

## Fase 0 — Setup del repositorio y herramientas

**Macro-objetivo:** dejar el monorepo navegable, con tooling reproducible, antes de escribir lógica.

### T0.1 — Inicializar `pyproject.toml` con `uv`

- **Entregable:** `pyproject.toml` declarando dependencias mínimas: `starlette`, `shiny`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `pydantic-settings`, `pandas`, `numpy`, `psycopg[binary]`, `python-dotenv`, `xlsxwriter`. Dev: `pytest`, `pytest-asyncio`, `hypothesis`, `playwright`, `ruff`, `black`, `mypy`, `pre-commit`, `rsconnect-python`.
- **Comando:** `uv init --package backend && uv add starlette shiny ... && uv add --dev pytest ...`
- **AC:** `uv sync` instala todo limpio en máquina vacía; `uv.lock` commiteado.

### T0.2 — Configurar `ruff`, `black`, `mypy`, `pre-commit`

- **Entregable:** `pyproject.toml` con `[tool.ruff]` (select `E,F,I,B,UP`), `[tool.black]` (line-length 100), `[tool.mypy]` (strict). `.pre-commit-config.yaml` con hooks de los tres.
- **AC:** `uv run pre-commit run -a` pasa en un repo recién clonado.

### T0.3 — Inicializar frontend Astro con `pnpm`

- **Entregable:** carpeta `frontend/` con plantilla Astro Empty + TypeScript Strict. `astro.config.mjs` con `output: 'static'`, `inlineStylesheets: 'always'`, proxy `/api` y `/shiny` a `localhost:8000`. Tailwind integrado.
- **Comandos:** `corepack enable && pnpm create astro@latest frontend` (después dentro de la carpeta) `pnpm install && pnpm approve-builds`.
- **AC:** `pnpm run dev` levanta Astro en `:4321`; `pnpm run build` produce `frontend/dist/` con CSS inline.

### T0.4 — `.gitignore`, `.rscignore`, `.env.example`, `docker-compose.yml`

- **Entregable:**
  - `.gitignore` ya existente + `backend/static/`, `frontend/dist/`, `var/*.db`, `.venv/`.
  - `.rscignore` siguiendo el patrón de `plan_replication.md` §5.
  - `.env.example` con `DATABASE_URL=sqlite:///./var/app.db`, `DEBOUNCE_MS=1500`, `SUPABASE_URL=`, `SUPABASE_KEY=`.
  - `docker-compose.yml` (opcional) con `postgres:16` para devs que prefieran no usar SQLite.
- **AC:** `cp .env.example .env && uv run python -c "from backend.settings import settings; print(settings)"` no falla.

### T0.5 — `scripts/dev.ps1`

- **Entregable:** script PowerShell que abre **dos terminales** (backend uvicorn + frontend pnpm dev). Modelo basado en `docs/doc_guia/ejecucion.md` §3.
- **AC:** `./scripts/dev.ps1` levanta ambos servicios; `localhost:4321` y `localhost:8000/shiny/` responden.

### T0.6 — Esqueleto de `app.py` y `backend/main.py`

- **Entregable:** `app.py` (entrypoint ShinyApps.io) con `Starlette(routes=[Mount("/shiny", ...), Mount("/", StaticFiles(...))])` y un Shiny mínimo de prueba (“Hello World”). `backend/main.py` análogo para dev con uvicorn `--reload`.
- **AC:** `uvicorn app:app --port 8000` muestra Hello en `localhost:8000/shiny/`.

---

## Fase 1 — Modelo de dominio puro

**Macro-objetivo:** definir las estructuras Pydantic que representan `ScenarioState` y `DerivedState`. Estas son la frontera entre persistencia, motor y UI; deben quedar **inmutables y serializables** antes de tocar SQL.

> Referencias: `description_proyecto.md` §1.1 (glosario), §3.2 (variedad), §3.3 (reglas).

### T1.1 — Enums y tipos primitivos

- **Entregable:** `backend/domain/enums.py`:
  - `class Productor(str, Enum): HF_INTERNA, HF_TERCEROS, TERCEROS`
  - `class BloqueKind(str, Enum): CRECIMIENTO_HF, RECAMBIO_VARIETAL, NUEVOS_TERCEROS`
  - `SeasonCode = Literal["T2627","T2728","T2829","T2930","T3031","T3132"]`
  - `PlantYear = Annotated[int, Field(ge=1, le=7)]`
- **AC:** `mypy --strict` pasa.

### T1.2 — Modelos de inputs

- **Entregable:** `backend/domain/inputs.py` con Pydantic models:
  - `BaseTableRow(project_name, unit, values: dict[SeasonCode, float], total: float)`
  - `BaseTable(rows: list[BaseTableRow], variation: dict[SeasonCode, float])` — *variation es input usuario*
  - `VarietyParamRow(plant_year: PlantYear, productividad, densidad, precio_estimado, pct_recaudacion)`
  - `Variety(name: str, params: list[VarietyParamRow])` con validador `@model_validator` que asegura `plant_year ∈ {1..7}` único y completo.
  - `Rules(royaltie_fob: float, costo_plantines: float, interes_financiamiento: float = 0.0, financiamiento_anios: int = 5)`
  - `NewProjectCell(bloque: BloqueKind, sub_proyecto: str, variety_name: str, season: SeasonCode, hectareas: float)`
  - `ScenarioState(name, country, base_table, varieties, rules, new_project_cells)`
- **AC:** instanciar el escenario canónico de UI.png desde un dict literal funciona.

### T1.3 — Modelos derivados

- **Entregable:** `backend/domain/derived.py`:
  - `CalculosVariedadCell(productor, plant_year, productividad_kg_ha, ganancia_fob_ha, ...)`
  - `MatrizSubyacente(bloque, sub_proyecto, variety_name, values: dict[(PlantYear, SeasonCode), float], kind: Literal["produccion","ganancia","plantines"])`
  - `Subtotales(bloque, variety_name, produccion: dict[SeasonCode, float], ganancia: dict, ganancia_plantines: dict | None)`
  - `Totales(hortifrut_fruta, hortifrut_ganancia, terceros_fruta, terceros_ganancia: dict[SeasonCode, float])`
  - `DerivedState(calculos_variedades, subtotales_por_bloque_variedad, totales)`
- **AC:** todos los modelos exportan a JSON estable.

### T1.4 — Validaciones cross-field

- **Entregable:** validators en `ScenarioState`:
  - todas las variedades referenciadas en `new_project_cells` existen,
  - todas las temporadas son secuenciales y dentro del rango del escenario,
  - `pct_recaudacion ∈ [0, 1]`, `royaltie_fob ∈ [0, 1]`, `financiamiento_anios > 0`.
- **AC:** tests negativos en `tests/unit/test_domain_validators.py` confirman cada error.

---

## Fase 2 — Motor de cálculo + golden tests

**Macro-objetivo:** implementar **toda la matemática** de `description_proyecto.md` §3 como funciones puras y validarla contra los CSVs de `docs/image/`.

> **Esta fase NO toca DB, NO toca API, NO toca UI.** Si los golden tests pasan aquí, el resto es plomería.

### T2.1 — Loader de fixtures desde `docs/image/*.csv`

- **Entregable:** `tests/conftest.py` con fixtures pytest que parsean `imagen1.csv` (Tabla Base), `imagen7.csv`, `imagen8.csv`, `imagen9.csv`, `imagen10.csv` (matrices subyacentes) y construyen el `ScenarioState` canónico de UI.png.
- **AC:** `pytest --collect-only` muestra fixtures `base_table_imagen1`, `scenario_ui_png`, `matriz_imagen7`, etc.

### T2.2 — `calculos_variedades.py` (§3.4)

- **Entregable:** función `compute_calculos_variedades(varieties, rules) -> dict[(variety, productor, plant_year), CalculosVariedadCell]`.
- **Detalle:**
  - HF Interna: `Prod = Productividad × Densidad`, `Gan = Precio × Prod`.
  - HF Terceros: `Prod = Productividad × Densidad × %Recaud`, `Gan_VentaPropia = ProdHFT × Precio × R`, `Gan_VentaProductor = ProdTerceros × Precio × R`.
  - Terceros: `Prod = ProdHFI × (1−%Recaud)`, `Gan_VentaHF = Precio × ProdHFT × (1−R)`, `Gan_VentaPropia = Precio × ProdTerceros × (1−R)`.
- **AC:** test unitario verifica para V1 año 1: `ProdHFI = 13,000`; año 4: `ProdHFT = 26,000`; año 5: `ProdTerceros = 9,750`.

### T2.3 — `lag_matrix.py` (§3.5)

- **Entregable:** helper `build_lag_matrix(ha_by_subrow_season, max_plant_year, seasons) -> DataFrame[plant_year × season]` que aplica `M[n, t] = ha(t − n)` con `DataFrame.shift(periods=n, axis=1)`.
- **AC:** `M[1, T2728] == ha[T2627]` y `M[5, T3132] == ha[T2728 − 4] = ha[T2627]` (con max_plant_year=5).

### T2.4 — `crecimiento_hf.py` (§3.6)

- **Entregable:** función `compute_block_crecimiento_hf(scenario, calculos) -> MatrizSubyacente + Subtotales` (un par por variedad).
- **AC:** `tests/golden/test_golden_imagen7_crecimiento.py` reproduce **exactamente** los valores de UI.png para V1 con CHAO=250@T2627 y OLMOS=200@T2728.

### T2.5 — `recambio.py` (§3.7)

- **Entregable:** misma firma que T2.4 (estructura idéntica).
- **AC:** golden test contra imagen 8 con OLMOS=50@T2728 (subtotales `650 / 975 / 1300 / 1625 / 1625` para producción).

### T2.6 — `nuevos_terceros.py` (§3.8.1)

- **Entregable:** función que usa `Productividad_HFTerceros` para producción y `Ganancia_Royaltie_VentaPropia + Ganancia_Royaltie_VentaProductor` para ganancia.
- **AC:** golden test contra imagen 9: subtotales `1,625 / 3,738 / 4,875 / 5,590 / 5,444` (producción) y `780 / 1,794 / 2,496 / 3,198 / 3,510` (ganancia).

### T2.7 — `plantines.py` (§3.8.2)

- **Entregable:** función con **máscara booleana** que aplica `n > Financiamiento ⇒ 0`. Acepta `interes_financiamiento` (hoy ignorado, hook listo para anualidad). Función pura `cuota_amortizacion(capital, i, n)` separada (TDD, no usada aún).
- **AC:** golden test contra imagen 9: subtotales plantines `569 / 1,024 / 1,024 / 1,024 / 1,024`. Test adicional: con `financiamiento=3`, T3031 y T3132 quedan en `0` para una siembra T2627.

### T2.8 — `terceros_totales.py` (§3.9)

- **Entregable:** función que aplica `ProducciónTerceros` y `GananciaTerceros` **solo** a las ha del bloque `NUEVOS_TERCEROS` (no B1 ni B2).
- **AC:** golden test contra imagen 10: subtotales `— / — / 325 / 1,073 / 1,869` (producción) y `5,720 / 13,156 / 18,304 / 23,452 / 25,740` (ganancia).

### T2.9 — `totales.py` (§3.10)

- **Entregable:** función `compute_totales(subtotales_por_bloque, subyacente_terceros_totales) -> Totales` sumando sobre variedades.
- **AC:** golden test contra UI.png sección 5 (todos los valores listados en *Datos de referencia*).

### T2.10 — `recompute.py` — orquestador

- **Entregable:** `recompute(scenario: ScenarioState) -> DerivedState` que encadena T2.2 → T2.9 en orden topológico.
- **AC:** `tests/simulation/test_user_flow_ui_png.py` arma `ScenarioState` canónico, llama `recompute`, y compara **todo el `DerivedState`** contra los goldens. Una sola llamada reproduce **toda la UI.png**.

### T2.11 — Tests property-based (Hypothesis)

- **Entregable:** `tests/property/test_invariants.py` con propiedades:
  - **No-negatividad:** todos los valores derivados ≥ 0 dado inputs ≥ 0.
  - **Idempotencia:** `recompute(s) == recompute(s)` bit-a-bit (hashing del JSON).
  - **Monotonía:** aumentar ha en un sub-proyecto nunca decrece la producción total.
  - **Linealidad:** `recompute(2·s) == 2·recompute(s)` salvo plantines truncados (verificar lineales solo en producción/ganancia, no plantines).
- **AC:** Hypothesis con `max_examples=200` no encuentra contraejemplos.

---

## Fase 3 — Persistencia: SQLAlchemy + SQLite dev + Supabase

**Macro-objetivo:** habilitar persistencia sin acoplarla al motor de cálculo (los repos retornan/aceptan modelos Pydantic del dominio).

> Referencia: `description_proyecto.md` §1.3, §1.5.

### T3.1 — Engine factory dual

- **Entregable:** `backend/db/session.py`. Si `DATABASE_URL` empieza con `postgresql://...pooler.supabase.com`, instanciar con `poolclass=NullPool` (validado vía Context7 sobre Supabase). Si SQLite, habilitar `connect_args={"check_same_thread": False}`.
- **AC:** test que parametriza ambas URLs y verifica el engine.

### T3.2 — Modelos ORM

- **Entregable:** `backend/db/models.py` con SQLAlchemy 2.x `Mapped[...]` siguiendo el esquema de `description_proyecto.md` §1.3. Campos JSON con `sqlalchemy.JSON` (no `JSONB`) para portabilidad.
- **AC:** `mypy --strict` y `alembic check` pasan.

### T3.3 — Alembic init + migración inicial

- **Entregable:** `alembic init alembic`, `env.py` configurado para leer `DATABASE_URL` y usar el `Base.metadata`. Migración `0001_initial.py` autogenerada.
- **AC:** `alembic upgrade head` corre limpio sobre SQLite vacío y sobre Supabase vacío.

### T3.4 — Seeds default

- **Entregable:** `backend/db/seeds.py` con la Tabla Base de imagen 1 y Reglas default. `scripts/seed_dev_db.py` la carga + carga el escenario canónico de UI.png para tests manuales.
- **AC:** tras `python scripts/seed_dev_db.py`, abrir SQLite con `sqlite3 var/app.db` muestra las tablas pobladas.

### T3.5 — Repositorios

- **Entregable:** `backend/db/repos.py` con repos `ScenarioRepo`, `VarietyRepo`, `RulesRepo`, `NewProjectsRepo`. Métodos retornan/aceptan modelos Pydantic.
- **AC:** `tests/integration/test_repos.py` con SQLite en memoria valida round-trip de `ScenarioState`.

### T3.6 — Audit log

- **Entregable:** decorador `@audited("entity_name")` que persiste cambios en `audit_log` (payload JSON).
- **AC:** test verifica que un `update_variety_params` produce un audit row.

---

## Fase 4 — API Starlette

**Macro-objetivo:** exponer CRUD + recompute + export, **antes** de tocar Shiny, para que el frontend pueda desarrollarse contra una API estable.

### T4.1 — Schemas Pydantic para request/response

- **Entregable:** `backend/api/schemas.py` con DTOs (no exponer los modelos ORM).
- **AC:** OpenAPI generada con `starlette-apispec` muestra los schemas.

### T4.2 — Rutas

- **Entregable:** `backend/api/routes.py` registrando:
  - `GET/POST /api/scenarios`
  - `GET/PUT/DELETE /api/scenarios/{id}`
  - `POST /api/scenarios/{id}/varieties`, `PUT /api/varieties/{id}/params`
  - `GET/PUT /api/scenarios/{id}/rules`
  - `PUT /api/scenarios/{id}/new-projects/{cell_id}` (edición de ha)
  - `POST /api/scenarios/{id}/recompute` → retorna `DerivedState`
  - `GET /api/scenarios/{id}/export.xlsx`
- **AC:** todos responden con códigos correctos en `tests/integration/test_api_*.py`.

### T4.3 — Recompute endpoint

- **Entregable:** lee scenario desde DB → construye `ScenarioState` → llama `recompute()` → retorna `DerivedState`.
- **AC:** `tests/integration/test_api_recompute.py` POSTea el escenario UI.png y compara el response contra los goldens.

### T4.4 — Export XLSX

- **Entregable:** `backend/api/exports.py` que produce un XLSX con 5 hojas (una por sección de la UI), formato numérico `#,##0` / `#,##0`, fondos ciruela/verde según UI.png. Usa `xlsxwriter`.
- **AC:** test que abre el XLSX exportado del escenario UI.png y verifica una celda de cada sección.

### T4.5 — Manejo de errores y validación

- **Entregable:** middleware Starlette que captura `ValidationError` de Pydantic → `422`, errores de dominio → `400`, integridad DB → `409`.
- **AC:** tests negativos cubren cada caso.

---

## Fase 5 — Aplicación Shiny

**Macro-objetivo:** construir la UI reactiva de `UI.png` consumiendo la API REST + manteniendo un `reactive.value(ScenarioState)` local con debounce.

> Referencia: `description_proyecto.md` §2 (wireframe ASCII).

### T5.1 — Layout maestro

- **Entregable:** `backend/shiny_app/app.py` con `ui.page_fluid` reproduciendo las 5 secciones del wireframe. `styles.css` con tokens ciruela (`#E7B6D1`) y verde (`#0E7C3E`).
- **AC:** screenshot visual coincide con UI.png (revisión manual).

### T5.2 — Bridge reactivo `state.py`

- **Entregable:** `reactive.value[ScenarioState]` central. Carga inicial desde API (`GET /api/scenarios/{id}`). Cualquier cambio en UI escribe vía API y actualiza el `value`.
- **AC:** test E2E (Fase 8) confirma que reload preserva estado.

### T5.3 — Helper de debounce

- **Entregable:** `backend/shiny_app/reactive_helpers.py` con `debounce(input_value, ms=1500)` basado en `reactive.invalidate_later` + un sello de tiempo (patrón validado con Context7: combinar `@reactive.calc` con `invalidate_later` para emitir el último valor estable).
- **AC:** test unitario simula tipeo rápido (5 cambios en 500 ms) y confirma 1 sola emisión final.

### T5.4 — Módulo `base_table.py` (Sección 1)

- **Entregable:** tabla editable + botón `[Confirmar Base]` que queda *read-only* tras confirmar (ver `description_proyecto.md` §2.1).
- **AC:** test E2E navega a sección 1, completa, confirma, intenta editar → bloqueado.

### T5.5 — Módulo `varieties_panel.py` (Sección 2)

- **Entregable:**
  - `[+ Agregar variedad]` con validación de campos no vacíos (incluido nombre),
  - tabla Variable × Año plegable,
  - filtro de variedades guardadas,
  - botón `[Hecho]` con `disabled=True` mientras haya `null`.
- **AC:** tests E2E para flujo crear/editar/eliminar variedad.

### T5.6 — Módulo `rules_panel.py` (Sección 3)

- **Entregable:** 4 campos editables verdes (Royaltie FOB, Costo Plantines, Interés, Financiamiento).
- **AC:** cambiar Financiamiento de 5 → 3 dispara recompute y los plantines de T3031/T3132 caen a 0.

### T5.7 — Módulo `new_projects.py` (Sección 4)

- **Entregable:**
  - filtro variedad,
  - 3 bloques con sub-filas dinámicas,
  - celdas ciruela editables con debounce 1.5 s,
  - sub-totales calculados *desde el server* (no recálculo local en JS).
- **AC:** test E2E del escenario UI.png; los subtotales coinciden con los goldens.

### T5.8 — Módulo `totals.py` (Sección 5)

- **Entregable:** tabla read-only de 4 filas (Hortifrut fruta/ganancia, Terceros fruta/ganancia).
- **AC:** test E2E verifica los 4×5 valores contra los goldens.

### T5.9 — Bloqueos UX

- **Entregable:** sección 4 deshabilitada con tooltip si no hay variedades; modal de confirmación al eliminar variedad con ha asignadas.
- **AC:** tests E2E negativos.

---

## Fase 6 — Integración Starlette ↔ Shiny ↔ estáticos

**Macro-objetivo:** mismo proceso atiende API, Shiny y los estáticos compilados de Astro.

### T6.1 — Mount order en `app.py`

- **Entregable:** rutas API → `Mount("/shiny", shiny_app)` → `Mount("/", StaticFiles(directory="backend/static", html=True))` (StaticFiles **siempre al final**, como en `plan_replication.md` §4.3).
- **AC:** `GET /api/status` retorna JSON; `GET /shiny/` retorna UI; `GET /` retorna `index.html` de Astro.

### T6.2 — Pipeline de build Astro → estáticos

- **Entregable:** `scripts/build.ps1`:
  ```powershell
  cd frontend; pnpm run build; cd ..
  uv run python scripts/inline_js.py
  xcopy /E /Y frontend\dist\* backend\static\
  ```
- **AC:** tras `./scripts/build.ps1`, `localhost:8000/` muestra el shell Astro.

### T6.3 — Verificación de rutas relativas

- **Entregable:** auditoría: `index.astro` usa `./api/...` y `<iframe src="./shiny/">` (nunca `/api/`).
- **AC:** test que recarga `localhost:8000/` no produce 404 en recursos.

---

## Fase 7 — Frontend Astro

**Macro-objetivo:** un shell estético, ligero, que provee header + auth placeholder + iframe a `/shiny/`. **Sin lógica de negocio.**

### T7.1 — `index.astro`

- **Entregable:** SPA single-page con título “Business Planning 2026 — Perú”, selector de escenario (mock para Fase 10), iframe ocupando el resto del viewport.
- **AC:** Lighthouse score Performance ≥ 90.

### T7.2 — Tokens Tailwind

- **Entregable:** `tailwind.config.cjs` con `colors.ciruela = '#E7B6D1'`, `colors.verde = '#0E7C3E'`.
- **AC:** los componentes Astro pueden usar `bg-ciruela`.

### T7.3 — Componentes mínimos

- **Entregable:** `Header.astro` (logo + título + user), `ScenarioSwitcher.astro` (placeholder).
- **AC:** revisión visual.

---

## Fase 8 — Tests E2E

### T8.1 — Setup Playwright

- **Entregable:** `playwright install chromium`, `conftest.py` con fixture `page` apuntando a `localhost:8000`.
- **AC:** `uv run pytest tests/e2e/ -v` arranca el browser.

### T8.2 — Flujo completo UI.png

- **Entregable:** `tests/e2e/test_playwright_flow.py` que:
  1. Crea escenario nuevo.
  2. Llena Tabla Base (datos imagen 1).
  3. Confirma Base.
  4. Crea variedad V1 con los parámetros de imagen 2.
  5. Ajusta Reglas (deja defaults).
  6. Llena ha de UI.png (CHAO=250@T2627, OLMOS=200@T2728, etc.).
  7. Espera el debounce.
  8. Verifica los **20+ valores** del Totales y de los subtotales.
- **AC:** test pasa en CI headless.

### T8.3 — Recarga y persistencia

- **Entregable:** recargar página tras paso 6 y verificar que los valores siguen ahí (sin error 404 — patrón SPA, `plan_replication.md` §3).
- **AC:** test E2E adicional.

---

## Fase 9 — Documentación

### T9.1 — `README.md` raíz

- **Entregable:** README ejecutivo:
  - Qué hace la app (link a `description_proyecto.md`).
  - Stack (link a §Stack tecnológico de este plan).
  - Quick start (3 comandos).
  - Cómo correr tests.
  - Cómo desplegar (link a `ejecucion.md`).
- **AC:** un dev nuevo levanta la app en < 15 min siguiendo solo el README.

### T9.2 — `ejecucion.md` raíz

- **Entregable:** réplica de la estructura de `docs/doc_guia/ejecucion.md` adaptada:
  - §1 Requisitos previos (Python ≥ 3.11, uv, Node ≥ 18, pnpm, Git, cuenta ShinyApps.io).
  - §2 Instalación local (uv venv, uv pip install, pnpm install).
  - §3 Ejecución dev (script `dev.ps1` + opción manual 2 terminales).
  - §4 Build prod (frontend → static).
  - §5 Despliegue ShinyApps.io con `rsconnect` (primer deploy + redeploy + `app-id`).
  - §6 Troubleshooting (404 al recargar, rutas absolutas, WebSocket, NumPy/Python 3.13).
  - §7 Tests (`pytest unit/`, `pytest golden/`, `pytest e2e/`).
- **AC:** un dev nuevo despliega a ShinyApps.io en < 1 hora siguiendo solo este archivo.

### T9.3 — Diagramas

- **Entregable:** en `docs/`, exportar el diagrama Mermaid de `description_proyecto.md` §1.2 como SVG. Agregar diagrama de despliegue (Astro → Starlette → Shiny + Supabase).
- **AC:** SVGs renderizan en GitHub.

---

## Fase 10 — Despliegue

### T10.1 — Provisión Supabase

- **Tareas:**
  1. Crear proyecto Supabase (free tier).
  2. Copiar **transaction pooler URL** (puerto **6543**) — recomendado en lugar de la URL directa.
  3. Setear `DATABASE_URL` en `.env` y en secrets de ShinyApps.io con el sufijo de workaround si aplica.
- **AC:** `alembic upgrade head` corre contra Supabase y crea las tablas.

### T10.2 — Adaptar `session.py` para Supabase

- **Entregable:** si la URL contiene `pooler.supabase.com`, usar `NullPool` (validado con Context7: Supavisor ya hace pooling, doble pooling causa bugs).
- **AC:** test integración con `DATABASE_URL` de Supabase pasa.

### T10.3 — `.rscignore` y `requirements.txt`

- **Entregable:** `.rscignore` siguiendo el patrón de `plan_replication.md` §5 (excluir `frontend/`, `node_modules/`, `notebooks/`, `docs/`, `tests/`, `scripts/`, `.venv/`). Generar `requirements.txt` con `uv pip compile pyproject.toml -o requirements.txt`.
- **AC:** `rsconnect deploy --dry-run` no incluye carpetas innecesarias.

### T10.4 — Primer deploy

- **Entregable:** comandos en `ejecucion.md` §5:
  ```powershell
  uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . \
    --entrypoint app:app --name <usuario> --title "HF-Breeding-Planner" --new
  ```
- **AC:** la app responde en `<usuario>.shinyapps.io/HF-Breeding-Planner/`.

### T10.5 — Redeploy automatizable

- **Entregable:** snippet en `ejecucion.md` para redeploy con `--app-id`.
- **AC:** un cambio trivial sube en < 5 min.

### T10.6 — Verificación post-deploy

- **Checklist** (basado en `doc_guia/ejecucion.md` §5.5):
  - [ ] URL pública accesible
  - [ ] Iframe Shiny carga
  - [ ] CRUD escenarios funciona contra Supabase
  - [ ] Subtotales coinciden con UI.png
  - [ ] Recarga NO da 404 (ver `plan_replication.md` §3)
  - [ ] Export XLSX descargable

---

## Apéndice A — Matriz de trazabilidad

| Sección de `description_proyecto.md` | Cubierta en                            |
| ------------------------------------ | -------------------------------------- |
| §1.1 Glosario                        | T1.1–T1.3                              |
| §1.2 DAG reactivo                    | T2.10 (recompute), T5.3 (debounce)     |
| §1.3 Modelo de datos                 | T3.2, T3.3                             |
| §1.4 Ciclo reactivo                  | T5.3                                   |
| §1.5 Persistencia / entornos         | T3.1, T10.1, T10.2                     |
| §2 UI/UX                             | Fase 5                                 |
| §2.1 Validaciones                    | T5.4, T5.5, T5.9                       |
| §2.2 Reactividad                     | T5.3                                   |
| §3.1 Tabla Base (variación = input)  | T5.4                                   |
| §3.2 Datos variedad                  | T1.2, T2.2                             |
| §3.3 Reglas                          | T2.2, T5.6                             |
| §3.4 Cálculos variedades             | T2.2                                   |
| §3.5 Lag fenológico                  | T2.3                                   |
| §3.6 Crecimiento HF                  | T2.4                                   |
| §3.7 Recambio                        | T2.5                                   |
| §3.8.1 Nuevos Prod Terceros          | T2.6                                   |
| §3.8.2 Plantines + truncamiento      | T2.7                                   |
| §3.9 Terceros para Totales (solo B3) | T2.8                                   |
| §3.10 Totales                        | T2.9                                   |
| §3.11 Unidades                       | Convención global de este plan         |

---

## Apéndice B — Riesgos técnicos y mitigaciones

| Riesgo                                                               | Probabilidad | Impacto | Mitigación                                                                                                                  |
| -------------------------------------------------------------------- | ------------ | ------- | --------------------------------------------------------------------------------------------------------------------------- |
| ShinyApps.io rompe rutas con worker slug dinámico                    | Media        | Alto    | SPA estricto (`plan_replication.md` §3), rutas relativas, `inlineStylesheets: 'always'`.                                    |
| Pooler de Supabase + pool de SQLAlchemy → conexiones colgadas        | Alta         | Alto    | `NullPool` cuando se detecta `pooler.supabase.com` (Context7-validated).                                                    |
| Debounce mal implementado dispara recompute en cada tecla            | Media        | Medio   | T5.3 con test específico de tipeo rápido.                                                                                   |
| Golden tests fallan por redondeo                                     | Alta         | Bajo    | Tolerancia `abs(diff) ≤ 1` para enteros, `rel=1e-3` para floats.                                                            |
| Migración `JSONB` SQLite ↔ Postgres                                  | Media        | Medio   | Usar `sqlalchemy.JSON` (no `JSONB`).                                                                                        |
| `numpy < 2.1` no compila en Python 3.13                              | Media        | Alto    | Fijar `numpy>=2.1.0` en `pyproject.toml`.                                                                                   |
| Variedades sin parámetros para Año N llegando al motor               | Baja         | Alto    | Validador Pydantic exige los 7 años (T1.2).                                                                                 |
| Cambios en Reglas no recalculan correctamente                        | Baja         | Alto    | Property test de idempotencia (T2.11) + test E2E de cambio Financiamiento (T5.6).                                           |

---

## Apéndice C — Definition of Done global

Un cambio sale de “in progress” solo si:

1. `uv run pre-commit run -a` pasa.
2. `uv run pytest tests/unit tests/golden tests/property` pasa.
3. Si toca API: `uv run pytest tests/integration` pasa.
4. Si toca UI: `uv run pytest tests/e2e` pasa en local.
5. Tests nuevos cubren el código nuevo (cobertura ≥ 80% en el archivo tocado).
6. No se introducen `TODO`/`FIXME` sin issue asociado.
7. Si afecta UI, screenshot adjunto en la PR.
8. Para cambios en lógica de negocio: golden tests siguen pasando contra UI.png.

---

> **Próximo paso recomendado.** Generar a partir de este plan el archivo `docs/plan/tareas.md` con un listado granular tipo *Kanban* (una fila por T-ID con estado, owner, estimación), y comenzar **Fase 0**.
