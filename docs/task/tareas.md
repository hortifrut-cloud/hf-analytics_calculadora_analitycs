# Listado de Tareas — HF Breeding Planner

> **Fuentes de contexto obligatorias para el agente que ejecute estas tareas:**
> - Spec funcional/lógico: [`docs/description_proyecto.md`](../description_proyecto.md)
> - Plan macro (Fases y arquitectura): [`docs/plan/plan_maestro.md`](../plan/plan_maestro.md)
> - Patrón de despliegue de referencia: [`docs/plan_replication.md`](../plan_replication.md)
> - Plantilla de ejecución: [`docs/doc_guia/ejecucion.md`](../doc_guia/ejecucion.md)
> - Goldens (datos reales validados): `docs/image/imagen{1..10}.{png,csv}` y `docs/image/UI.png`
>
> **Convenciones de checkbox**
> - `[ ]` Pendiente
> - `[/]` En progreso / en espera
> - `[X]` Completado
>
> **Convenciones de IDs**
> - **Fase:** `F{n}` — ej. `F2`
> - **Tarea:** `T{f}.{n}` — ej. `T2.4`
> - **Acción:** `A{f}.{t}.{n}` — ej. `A2.4.1`
>
> **Regla maestra.** Cada Acción declara: **Objetivo · Input · Output · Proceso · Referencia/Lógica · Tests · Criterios de Aceptación (AC)**. Cada Tarea y Fase declara su propio Objetivo/AC. Una Tarea solo se marca completada si todas sus Acciones están en `[X]` y sus AC se cumplen; una Fase solo se marca completada si todas sus Tareas lo están.

---

## Índice

- [Fase 0 — Setup del repositorio](#fase-0--setup-del-repositorio-y-herramientas)
- [Fase 1 — Modelo de dominio puro](#fase-1--modelo-de-dominio-puro)
- [Fase 2 — Motor de cálculo + golden tests](#fase-2--motor-de-cálculo--golden-tests)
- [Fase 3 — Persistencia](#fase-3--persistencia-sqlalchemy--sqlite-dev--supabase)
- [Fase 4 — API Starlette](#fase-4--api-starlette)
- [Fase 5 — Aplicación Shiny](#fase-5--aplicación-shiny)
- [Fase 6 — Integración Starlette ↔ Shiny ↔ estáticos](#fase-6--integración-starlette--shiny--estáticos)
- [Fase 7 — Frontend Astro](#fase-7--frontend-astro)
- [Fase 8 — Tests E2E](#fase-8--tests-e2e)
- [Fase 9 — Documentación](#fase-9--documentación)
- [Fase 10 — Despliegue](#fase-10--despliegue-supabase--shinyappsio)

---

## [X] Fase 0 — Setup del repositorio y herramientas

- **Objetivo:** monorepo navegable con tooling reproducible (uv, pnpm, ruff, pre-commit, Astro skeleton, Starlette+Shiny “hello world”).
- **AC global de la Fase:**
  - `uv sync` instala todo limpio en máquina vacía.
  - `pnpm install && pnpm run build` produce `frontend/dist/`.
  - `uv run pre-commit run -a` pasa.
  - `uvicorn app:app --port 8000` responde en `/shiny/` con un “Hello”.
- **Referencias:** `plan_maestro.md` §Fase 0; `plan_replication.md` §4 completo.

---

### [X] T0.1 — Inicializar `pyproject.toml` con `uv`

- **Objetivo:** dejar el entorno Python listo y bloqueado.
- **AC:** `uv sync` instala sin errores; `uv.lock` commiteado; `python -c "import starlette, shiny, sqlalchemy, pandas, numpy"` no falla.

#### [X] A0.1.1 — Crear proyecto uv y dependencias runtime

- **Objetivo:** inicializar el `pyproject.toml` con dependencias de producción.
- **Input:** repo vacío (o con docs/ existente), Python ≥ 3.11 instalado.
- **Output:** `pyproject.toml`, `.python-version`, `uv.lock`.
- **Proceso:**
  1. `uv init --package hf-breeding-planner`
  2. `uv python pin 3.11` (o `3.13` si se desea — recordar `numpy>=2.1.0`).
  3. Agregar deps runtime:
     ```bash
     uv add starlette "shiny>=1.2" "uvicorn[standard]" \
            "sqlalchemy>=2.0.36" alembic \
            "pydantic>=2.6" pydantic-settings \
            "pandas>=2.2" "numpy>=2.1" \
            "psycopg[binary]>=3.2" python-dotenv xlsxwriter
     ```
- **Tests:** `uv run python -c "import starlette, shiny, sqlalchemy, pandas, numpy, psycopg, xlsxwriter; print('ok')"`
- **AC:** comando anterior imprime `ok` sin warnings.

#### [X] A0.1.2 — Agregar dependencias de desarrollo

- **Objetivo:** habilitar testing/lint/typing.
- **Input:** A0.1.1 hecho.
- **Output:** sección `[tool.uv.dev-dependencies]` en `pyproject.toml`.
- **Proceso:**
  ```bash
  uv add --dev pytest pytest-asyncio pytest-cov hypothesis \
                playwright ruff black mypy pre-commit rsconnect-python
  uv run playwright install chromium
  ```
- **Tests:** `uv run pytest --version`, `uv run ruff --version`, `uv run mypy --version`.
- **AC:** todos imprimen versión.

#### [X] A0.1.3 — Verificar reproducibilidad

- **Objetivo:** asegurar que un clon nuevo funcione.
- **Input:** `uv.lock` commiteado.
- **Output:** documento mental de que `git clone && uv sync` basta.
- **Proceso:** borrar `.venv/` local y correr `uv sync`.
- **Tests:** N/A (manual).
- **AC:** instalación completa < 60 s sin internet caché-fría < 3 min.

---

### [X] T0.2 — Configurar `ruff`, `black`, `mypy`, `pre-commit`

- **Objetivo:** estandarizar formato, lints y tipos antes de escribir lógica.
- **AC:** `uv run pre-commit run -a` pasa sobre el repo recién creado.

#### [X] A0.2.1 — Configurar ruff y black en `pyproject.toml`

- **Objetivo:** reglas únicas, line-length 100.
- **Input:** `pyproject.toml` de A0.1.1.
- **Output:** secciones `[tool.ruff]` y `[tool.black]`.
- **Proceso:** agregar
  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py311"
  [tool.ruff.lint]
  select = ["E", "F", "I", "B", "UP", "SIM", "ANN"]
  ignore = ["ANN101", "ANN102"]
  [tool.black]
  line-length = 100
  ```
- **Tests:** `uv run ruff check .` y `uv run black --check .` pasan.
- **AC:** sin errores ni warnings.

#### [X] A0.2.2 — Configurar mypy estricto

- **Objetivo:** tipado estricto desde el día 1.
- **Output:** `[tool.mypy]` en `pyproject.toml`.
- **Proceso:**
  ```toml
  [tool.mypy]
  strict = true
  python_version = "3.11"
  plugins = ["pydantic.mypy"]
  exclude = ["frontend/", "alembic/versions/"]
  ```
- **Tests:** `uv run mypy backend/` (cuando exista) corre sin errores.
- **AC:** primera ejecución limpia (módulos vacíos).

#### [X] A0.2.3 — pre-commit hooks

- **Objetivo:** evitar commits sucios.
- **Output:** `.pre-commit-config.yaml`.
- **Proceso:** hooks `ruff`, `ruff-format` (o `black`), `mypy`, `trailing-whitespace`, `end-of-file-fixer`. Instalar con `uv run pre-commit install`.
- **Tests:** crear archivo `.py` con `import os, sys` (orden mal) → `git commit` falla con sugerencia de ruff.
- **AC:** hook bloquea commit incorrecto y permite el corregido.

---

### [X] T0.3 — Inicializar frontend Astro con `pnpm`

- **Objetivo:** dejar `frontend/` listo para construir como SPA estática.
- **AC:** `cd frontend && pnpm run build` produce `dist/` con HTML cuyo CSS está inline.

#### [X] A0.3.1 — Habilitar `pnpm` vía corepack

- **Proceso:** `corepack enable && corepack prepare pnpm@latest --activate`.
- **Tests:** `pnpm --version` imprime versión.
- **AC:** ≥ 9.0.

#### [X] A0.3.2 — Crear plantilla Astro

- **Proceso:** `pnpm create astro@latest frontend` → Empty project, TypeScript Strict, **NO** instalar deps.
- Después: `cd frontend && pnpm install && pnpm approve-builds`.
- **Tests:** `pnpm run dev` levanta `localhost:4321`.
- **AC:** página por defecto carga.

#### [X] A0.3.3 — Configurar `astro.config.mjs` para SPA + ShinyApps.io

- **Objetivo:** evitar rutas absolutas `/_astro/...` que rompen en ShinyApps.io.
- **Proceso:**
  ```js
  // frontend/astro.config.mjs
  import { defineConfig } from 'astro/config';
  export default defineConfig({
    output: 'static',
    build: { inlineStylesheets: 'always' },
    vite: {
      server: {
        proxy: {
          '/api':   { target: 'http://localhost:8000', changeOrigin: true },
          '/shiny': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
        },
      },
    },
  });
  ```
- **Tests:** `pnpm run build` y verificar que `dist/index.html` tenga `<style>` inline.
- **AC:** no quedan referencias a `/_astro/*.css` como `<link rel="stylesheet">`.

#### [X] A0.3.4 — Instalar Tailwind y tokens

- **Proceso:** `pnpm dlx astro add tailwind`; configurar `tailwind.config.cjs` con
  ```js
  theme: { extend: { colors: { ciruela: '#E7B6D1', verde: '#0E7C3E' } } }
  ```
- **Tests:** un `<div class="bg-ciruela">` se ve color ciruela en dev.
- **AC:** revisión visual ok.

---

### [X] T0.4 — `.gitignore`, `.rscignore`, `.env.example`, `docker-compose.yml`

- **Objetivo:** archivos de configuración del repo.
- **AC:** `cp .env.example .env` permite arrancar el proyecto sin errores.

#### [X] A0.4.1 — Actualizar `.gitignore`

- **Proceso:** añadir `backend/static/`, `frontend/dist/`, `frontend/node_modules/`, `var/*.db`, `.venv/`.
- **AC:** `git status` ignora estos paths.

#### [X] A0.4.2 — Crear `.rscignore`

- **Proceso:** copiar y adaptar el bloque de `plan_replication.md` §5 (excluye `frontend/`, `node_modules/`, `notebooks/`, `docs/`, `tests/`, `scripts/`, `.venv/`).
- **Tests:** `rsconnect deploy --dry-run` (cuando exista cuenta) no incluye esos paths.
- **AC:** archivo presente, sintaxis válida (líneas no comentadas no contienen espacios extra).

#### [X] A0.4.3 — `.env.example`

- **Objetivo:** plantilla de variables de entorno.
- **Proceso:**
  ```env
  # Local (SQLite)
  DATABASE_URL=sqlite:///./var/app.db
  # Cloud (Supabase transaction pooler — port 6543)
  # DATABASE_URL=postgresql+psycopg://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:6543/postgres
  DEBOUNCE_MS=1500
  LOG_LEVEL=INFO
  # rsconnect (ShinyApps.io)
  rsconnect_usuario=
  rsconnect_name=
  rsconnect_token=
  rsconnect_secret=
  ```
- **Tests:** `python -c "from dotenv import load_dotenv; load_dotenv('.env.example'); import os; assert os.environ['DEBOUNCE_MS']=='1500'"`.
- **AC:** todos los nombres documentados en `backend/settings.py` aparecen aquí.

#### [ ] A0.4.4 — `docker-compose.yml` (opcional)

- **Proceso:** servicio `postgres:16` con healthcheck, volumen persistente, puerto 5432.
- **Tests:** `docker compose up -d postgres && docker compose exec postgres pg_isready`.
- **AC:** servicio healthy.

---

### [X] T0.5 — `scripts/dev.ps1`

- **Objetivo:** arranque dev en un solo comando.
- **AC:** `./scripts/dev.ps1` levanta backend en `:8000` y Astro en `:4321`.

#### [X] A0.5.1 — Script PowerShell con 2 terminales

- **Input:** `app.py` ya creado (A0.6.x).
- **Proceso:** usar `Start-Process powershell -ArgumentList ...` para abrir dos ventanas: una con `uv run uvicorn app:app --reload --port 8000 --reload-exclude ".venv"`, otra con `cd frontend; pnpm run dev`.
- **Tests:** ejecutar y verificar ambas URLs.
- **AC:** ambos servicios responden HTTP 200 en sus rutas raíz.

---

### [X] T0.6 — Esqueleto `app.py` + Shiny “Hello”

- **Objetivo:** ASGI mount mínimo funcionando.
- **AC:** `localhost:8000/shiny/` muestra `Hello`.

#### [X] A0.6.1 — Shiny mínimo en `backend/shiny_app/app.py`

- **Proceso:**
  ```python
  from shiny import App, ui
  app_ui = ui.page_fluid(ui.h1("Hello — HF Breeding Planner"))
  def server(input, output, session): pass
  app = App(app_ui, server)
  ```
- **AC:** `uv run python -m shiny run backend/shiny_app/app.py` muestra la página.

#### [X] A0.6.2 — Entrypoint `app.py` raíz (Starlette + mounts)

- **Proceso:**
  ```python
  from starlette.applications import Starlette
  from starlette.responses import JSONResponse
  from starlette.routing import Route, Mount
  from starlette.staticfiles import StaticFiles
  from backend.shiny_app.app import app as shiny_app

  async def status(_): return JSONResponse({"status": "ok"})

  routes = [
      Route("/api/status", status),
      Mount("/shiny", app=shiny_app),
      Mount("/", app=StaticFiles(directory="backend/static", html=True), name="static"),
  ]
  app = Starlette(routes=routes)
  ```
- **Nota crítica:** `Mount("/", StaticFiles)` SIEMPRE al final, como dicta `plan_replication.md` §4.3.
- **Tests:** `curl localhost:8000/api/status` → `{"status":"ok"}`; `curl localhost:8000/shiny/` → HTML.
- **AC:** los 3 mounts responden.

#### [X] A0.6.3 — `backend/main.py` para dev

- **Proceso:** alias delgado que re-exporta `app` desde `app.py` para `uvicorn backend.main:app` (no usado en prod).
- **AC:** comando alternativo de dev funciona.

---

## [X] Fase 1 — Modelo de dominio puro

- **Objetivo:** clases Pydantic inmutables para `ScenarioState` y `DerivedState`. Frontera limpia entre DB ↔ motor ↔ UI.
- **AC global:**
  - `mypy --strict backend/domain/` pasa.
  - Construir el escenario canónico de `UI.png` desde un dict literal de Python no falla.
  - Tests negativos cubren cada validador.
- **Referencias:** `description_proyecto.md` §1.1, §3.2, §3.3; `plan_maestro.md` §Fase 1.

---

### [X] T1.1 — Enums y tipos primitivos

- **Objetivo:** vocabulario común tipado.
- **AC:** importar `Productor, BloqueKind, SeasonCode, PlantYear` desde otro módulo sin errores mypy.

#### [X] A1.1.1 — `backend/domain/enums.py`

- **Input:** N/A.
- **Output:** archivo con `Productor`, `BloqueKind`, `SeasonCode`, `PlantYear`.
- **Lógica:**
  ```python
  from enum import Enum
  from typing import Annotated, Literal
  from pydantic import Field

  class Productor(str, Enum):
      HF_INTERNA = "hf_interna"
      HF_TERCEROS = "hf_terceros"
      TERCEROS = "terceros"

  class BloqueKind(str, Enum):
      CRECIMIENTO_HF = "crecimiento_hf"
      RECAMBIO_VARIETAL = "recambio_varietal"
      NUEVOS_TERCEROS = "nuevos_terceros"

  SeasonCode = Literal["T2627","T2728","T2829","T2930","T3031","T3132"]
  PlantYear = Annotated[int, Field(ge=1, le=7)]
  ```
- **Tests:** `tests/unit/test_enums.py` que itera valores esperados.
- **AC:** mypy strict + test pasa.

---

### [X] T1.2 — Modelos de inputs (Pydantic)

- **Objetivo:** representar la entrada total del usuario.
- **AC:** instanciar el escenario UI.png desde un dict canónico produce un objeto válido sin warnings.
- **Referencia:** `description_proyecto.md` §3.1, §3.2, §3.3.

#### [X] A1.2.1 — `BaseTable` (imagen 1)

- **Objetivo:** modelar la Tabla Base con `variación` como input.
- **Output:** clases en `backend/domain/inputs.py`.
- **Lógica:**
  ```python
  class BaseTableRow(BaseModel):
      project_name: str
      unit: str
      values: dict[SeasonCode, float]
      total: float  # suma horizontal (puede validarse contra values)

  class BaseTable(BaseModel):
      rows: list[BaseTableRow]
      variation: dict[SeasonCode, float]   # input usuario (§3.1)
  ```
- **Tests:** crear la Tabla Base de imagen 1 e instanciarla.
- **AC:** `sum(row.values.values()) ≈ row.total` para cada fila (validator con tolerancia 1).

#### [X] A1.2.2 — `Variety` + `VarietyParamRow` (imagen 2/3)

- **Lógica:**
  ```python
  class VarietyParamRow(BaseModel):
      plant_year: PlantYear
      productividad: float        # Kg/planta
      densidad: float             # planta/ha
      precio_estimado: float      # FOB/kg
      pct_recaudacion: float = Field(ge=0, le=1)

  class Variety(BaseModel):
      name: str = Field(min_length=1)
      params: list[VarietyParamRow]

      @model_validator(mode="after")
      def _check_years(self):
          years = {p.plant_year for p in self.params}
          if years != set(range(1, 8)):
              raise ValueError("Faltan o sobran años de planta (debe ser {1..7})")
          return self
  ```
- **Tests:** crear V1 canónica; test negativo con 6 años → falla.
- **AC:** ambos casos cumplen.

#### [X] A1.2.3 — `Rules` (imagen 5)

- **Lógica:**
  ```python
  class Rules(BaseModel):
      royaltie_fob: float = Field(default=0.12, ge=0, le=1)
      costo_plantines: float = Field(default=3.5, ge=0)
      interes_financiamiento: float = Field(default=0.0, ge=0)
      financiamiento_anios: int = Field(default=5, ge=1, le=20)
  ```
- **Tests:** defaults instanciables sin argumentos.
- **AC:** `Rules().royaltie_fob == 0.12`.

#### [X] A1.2.4 — `NewProjectCell`

- **Lógica:** clave única `(bloque, sub_proyecto, variety_name, season)`. Una lista de estos representa toda la grilla editable.
  ```python
  class NewProjectCell(BaseModel):
      bloque: BloqueKind
      sub_proyecto: str       # 'CHAO','OLMOS','Talsa','Diamond Bridge'
      variety_name: str
      season: SeasonCode
      hectareas: float = Field(ge=0)
  ```
- **Tests:** instanciar las 5 celdas no-cero de UI.png.
- **AC:** todas se construyen.

#### [X] A1.2.5 — `ScenarioState`

- **Lógica:**
  ```python
  class ScenarioState(BaseModel):
      name: str
      country: str = "Perú"
      base_table: BaseTable
      varieties: list[Variety]
      rules: Rules
      new_project_cells: list[NewProjectCell]
      model_config = ConfigDict(frozen=True)  # inmutable
  ```
- **Tests:** ensamblar el escenario UI.png completo (todos los datos de §Datos de referencia del `plan_maestro.md`).
- **AC:** `ScenarioState.model_dump_json()` es determinístico (mismo input ⇒ mismo string).

---

### [X] T1.3 — Modelos derivados

- **Objetivo:** estructura de salida del motor de cálculo.
- **AC:** `DerivedState` se serializa a JSON y se reconstruye sin pérdida.

#### [X] A1.3.1 — `CalculosVariedadCell` (resultado §3.4)

- **Lógica:** una celda por `(variety, productor, plant_year)` con las columnas relevantes para cada productor (algunas vacías según productor). Considerar un modelo polimórfico simple con campos opcionales o tres modelos distintos discriminados por `productor`.
- **Tests:** construir HFI año 1 V1: `productividad_kg_ha=13_000, ganancia_fob_ha=52_000`.
- **AC:** roundtrip JSON.

#### [X] A1.3.2 — `MatrizSubyacente`

- **Lógica:** llaves `(plant_year, season)` → float. Atributo `kind ∈ {'produccion','ganancia','plantines'}`. Atributo `bloque, sub_proyecto, variety_name`.
- **AC:** representar imagen 7 completa como `MatrizSubyacente`.

#### [X] A1.3.3 — `Subtotales` y `Totales`

- **Lógica:** sub-totales por temporada para cada bloque/variedad; totales agregados Hortifrut + Terceros.
- **AC:** representar la sección 4 + 5 de UI.png como objetos válidos.

#### [X] A1.3.4 — `DerivedState` contenedor

- **Lógica:** agrupa los tres anteriores. Implementa `__eq__` natural por Pydantic.
- **Tests:** dos `DerivedState` calculados del mismo `ScenarioState` son iguales (idempotencia, F2).
- **AC:** test futuro pasa.

---

### [X] T1.4 — Validaciones cross-field

- **Objetivo:** detectar inputs inválidos antes de llegar al motor.
- **AC:** cada error tiene su test negativo.

#### [X] A1.4.1 — Validador: variedades referenciadas existen

- **Lógica:** `@model_validator(mode='after')` en `ScenarioState` que verifica `{cell.variety_name} ⊆ {variety.name}`.
- **Tests:** crear escenario con celda apuntando a variedad inexistente → `ValidationError`.
- **AC:** error message claro: `Variedad 'X' no existe en el escenario`.

#### [X] A1.4.2 — Validador: temporadas dentro del rango

- **Lógica:** verificar que todas las `SeasonCode` usadas pertenezcan al rango `[start_season, end_season]` (por defecto T2627..T3132).
- **Tests:** celda en T2526 → error.
- **AC:** test pasa.

#### [X] A1.4.3 — Validador: sub-proyectos por bloque

- **Lógica:** B1/B2 admiten `{CHAO, OLMOS, ...}`; B3 admite `{Talsa, Diamond Bridge, ...}`. **Extensible:** se permite cualquier string no vacío para no romper escenarios futuros, pero se warn-loggea si no es uno de los conocidos.
- **Tests:** valor desconocido en B3 → registro en log, no error.
- **AC:** se observa warn en captura de log.

---

## [X] Fase 2 — Motor de cálculo + golden tests

- **Objetivo:** implementar **toda** la matemática de `description_proyecto.md` §3 y validarla contra los CSVs de `docs/image/`.
- **AC global:**
  - Golden tests contra imágenes 7, 8, 9, 10 y UI.png pasan.
  - Property tests Hypothesis (`max_examples=200`) sin contraejemplos.
  - Sin I/O en `backend/logic/*`.
- **Referencias:** `description_proyecto.md` §3 completo; `plan_maestro.md` §Datos de referencia para los valores esperados.

---

### [X] T2.1 — Loader de fixtures desde `docs/image/*.csv`

- **Objetivo:** que pytest reciba directamente los CSVs como `pd.DataFrame` y el `ScenarioState` canónico.
- **AC:** `pytest --collect-only` muestra los fixtures.

#### [X] A2.1.1 — Parser de `imagen1.csv` (Tabla Base)

- **Input:** archivo `docs/image/imagen1.csv` (cabecera + 3 proyectos + Total + variación).
- **Output:** fixture `base_table_imagen1: BaseTable`.
- **Proceso:** leer con `pandas.read_csv`, mapear filas, construir `BaseTable`.
- **Tests:** test que verifica `base_table_imagen1.rows[0].values["T2627"] == 37`.
- **AC:** ok.

#### [X] A2.1.2 — Fixture `scenario_ui_png`

- **Output:** `ScenarioState` con V1 + 5 celdas de ha de UI.png.
- **Proceso:** construir desde literales Python (no parsear PNG). Los valores vienen de `plan_maestro.md` §Datos de referencia.
- **Tests:** `scenario_ui_png.varieties[0].params[0].productividad == 2`.
- **AC:** ok.

#### [X] A2.1.3 — Parsers de matrices `imagen{7,8,9,10}.csv`

- **Output:** fixtures `matriz_imagen7..10` como `dict[(plant_year, season), float]` para sub-totales y filas individuales.
- **Proceso:** parsear CSV (cuidando filas en blanco), extraer filas Año k producción / ganancia / plantines.
- **Tests:** `matriz_imagen9["sub_total_ganancia"]["T2728"] == 780`.
- **AC:** todas las filas amarillas (sub-totales) son accesibles.

---

### [X] T2.2 — `calculos_variedades.py` (§3.4)

- **Objetivo:** matriz `(variety × productor × plant_year)` con productividades y ganancias.
- **AC:** valores HFI/HFT/Terceros para V1 coinciden con valores teóricos (verificados a mano en `plan_maestro.md`).

#### [X] A2.2.1 — Hortifrut Producción Interna

- **Objetivo:** `Prod = Productividad × Densidad`; `Gan = Precio × Prod`.
- **Tests:** V1 año 1 → `Prod = 13_000`, `Gan = 52_000`. V1 año 5 → `Prod = 32_500`.
- **AC:** test pasa.

#### [X] A2.2.2 — Hortifrut Producción Terceros

- **Objetivo:** `ProdHFT = Productividad × Densidad × %Recaud`. Ganancia venta propia = `ProdHFT × Precio × R`. Ganancia venta productor = `ProdTerceros × Precio × R`.
- **Tests:** V1 año 1 → `ProdHFT = 13_000` (recaud=100%), Gan venta propia = `6_240`, Gan venta productor = `0`. V1 año 5 → `ProdHFT = 22_750`, Gan venta propia = `10_920`, Gan venta productor = `4_680`.
- **AC:** test pasa.

#### [X] A2.2.3 — Terceros (externo)

- **Objetivo:** `Prod = ProdHFI × (1 − %Recaud)`. Ganancia venta HF = `Precio × ProdHFT × (1 − R)`. Ganancia venta propia = `Precio × ProdTerceros × (1 − R)`.
- **Tests:** V1 año 5 → `ProdTerceros = 9_750`, ambas ganancias.
- **AC:** test pasa.

#### [X] A2.2.4 — Orquestador `compute_calculos_variedades`

- **Lógica:** ensamblar las tres en un dict indexado por `(variety, productor, plant_year)`.
- **Tests:** `tests/unit/test_calculos_variedades.py` cubre A2.2.1–A2.2.3.
- **AC:** cobertura ≥ 95% del archivo.

---

### [X] T2.3 — `lag_matrix.py` (§3.5)

- **Objetivo:** helper para construir matrices `M[n, t] = ha(t − n)`.
- **AC:** `M[1, T2728] == ha[T2627]`; offset correcto.

#### [X] A2.3.1 — `build_lag_matrix`

- **Lógica:**
  ```python
  def build_lag_matrix(
      ha_by_season: dict[SeasonCode, float],
      max_plant_year: int,
      seasons: list[SeasonCode],
  ) -> pd.DataFrame:
      base = pd.Series(ha_by_season).reindex(seasons).fillna(0.0)
      data = {n: base.shift(periods=n).fillna(0.0).values for n in range(1, max_plant_year + 1)}
      return pd.DataFrame(data, index=seasons).T  # filas plant_year, columnas season
  ```
- **Tests:** ha=`{T2627: 100, T2728: 50}` con max_plant_year=5 ⇒ `M[1, T2728]=100`, `M[2, T2829]=100`, `M[1, T2829]=50`.
- **AC:** test exacto.

#### [X] A2.3.2 — Agregador por sub-proyecto

- **Lógica:** suma de ha por temporada **sobre los sub-proyectos** del bloque/variedad antes de aplicar el shift.
- **Tests:** B3 V1 (Talsa T2627=100 + Diamond Bridge T2627=25) ⇒ agregado T2627 = 125.
- **AC:** ok.

---

### [X] T2.4 — `crecimiento_hf.py` (§3.6)

- **Objetivo:** producir `MatrizSubyacente` y `Subtotales` del bloque B1 por variedad.
- **AC:** golden test contra imagen 7 + sub-totales de UI.png.

#### [X] A2.4.1 — Función `compute_block_crecimiento_hf`

- **Lógica:**
  ```python
  Producción(n, t)  = ha_agg(t - n) × ProdHFI(V, año=n) / 1000
  Ganancia(n, t)    = ha_agg(t - n) × GanFOB_HFI(V, año=n) / 1000
  ```
- **Tests unitarios:** celdas específicas:
  - `Producción[Año1, T2728] = 250 × 13_000 / 1000 = 3_250`
  - `Producción[Año5, T3132] = 250 × 32_500 / 1000 = 8_125`
  - Sub-total producción T2829 = `3_250 + 4_225 = 7_475` (Año1 200×13/1000 + Año2 250×16,5)
- **AC:** valores exactos.

#### [X] A2.4.2 — Golden test imagen 7

- **Tests:** `tests/golden/test_golden_imagen7_crecimiento.py` carga `matriz_imagen7` y compara TODA la matriz vs. el output.
- **AC:** subtotales producción `[3_250, 7_475, 10_400, 13_325, 14_625]` (T2728..T3132), ganancia `[13_000, 29_900, 41_600, 53_300, 58_500]`. Tolerancia `abs ≤ 1`.

---

### [X] T2.5 — `recambio.py` (§3.7)

- **Objetivo:** misma estructura que T2.4.
- **AC:** golden contra imagen 8.

#### [X] A2.5.1 — Implementación

- **Lógica:** reutilizar internamente el motor de T2.4 parametrizado por `BloqueKind.RECAMBIO_VARIETAL`. Idealmente extraer una función `_compute_hf_internal_block(bloque_kind, scenario, calculos)`.
- **Tests:** golden test contra imagen 8 (OLMOS=50@T2728 ⇒ subtotales `[650, 975, 1300, 1625, 1625]` y `[2600, 3900, 5200, 6500, 6500]`).
- **AC:** test exacto.

---

### [X] T2.6 — `nuevos_terceros.py` (§3.8.1)

- **Objetivo:** bloque B3 con su lógica específica.
- **AC:** golden imagen 9 (filas producción y ganancia, **no** plantines — eso es T2.7).

#### [X] A2.6.1 — Producción

- **Lógica:** `Producción(n, t) = ha_agg(t − n) × ProdHFT(V, n) / 1000`.
- **Tests:** Año 1 T2728 con ha=125 (Talsa 100 + Diamond Bridge 25) ⇒ `125 × 13_000 / 1000 = 1_625`. Sub-total producción T2829 = `1_300 + 2_438 = 3_738` (Año1 con 100ha + Año2 con 125ha).
- **AC:** valores cuadran con imagen 9.

#### [X] A2.6.2 — Ganancia (suma de ambas royaltías)

- **Lógica:** `Ganancia(n, t) = ha_agg(t − n) × (GanRoyVentaPropia(V, n) + GanRoyVentaProductor(V, n)) / 1000`.
- **Tests:**
  - Año 1 T2728: `125 × (6_240 + 0) / 1000 = 780` ✓
  - Año 4 T3132 (ha=100 desde T2728): `100 × (12_480 + 3_120) / 1000 = 1_560` ✓
  - Año 5 T3132 (ha=125 desde T2627): `125 × (10_920 + 4_680) / 1000 = 1_950` ✓
- **AC:** sub-totales `[780, 1_794, 2_496, 3_198, 3_510]`.

---

### [X] T2.7 — `plantines.py` (§3.8.2)

- **Objetivo:** Ganancia Plantines con tope por `Financiamiento`.
- **AC:** golden imagen 9 sub-total plantines `[569, 1_024, 1_024, 1_024, 1_024]`.

#### [X] A2.7.1 — Fórmula base (lineal, sin interés)

- **Lógica:** `GP(n, t) = ha_agg(t − n) × Densidad(V, n) × Costo_Plantines / Financiamiento / 1000`.
- **Tests:** Año 1 T2728: `125 × 6_500 × 3.5 / 5 / 1000 = 568.75` → redondeo a `569`.
- **AC:** valor numérico ok.

#### [X] A2.7.2 — Máscara de truncamiento por `Financiamiento`

- **Lógica:** `GP(n, t) = 0  si  n > Financiamiento_anios`.
- **Tests:**
  - Default 5 años: con siembra única en T2627, plantines en T2728..T3132 (5 valores).
  - `financiamiento_anios=3`: plantines solo en T2728, T2829, T2930; T3031 y T3132 son 0 para esa siembra.
- **AC:** ambos casos pasan.

#### [X] A2.7.3 — Hook `cuota_amortizacion` (futuro)

- **Lógica:** función pura `cuota_amortizacion(capital, i, n) -> float` con `Cuota = Capital × i / (1 − (1+i)^(−n))`. Por ahora **no usada** en el cálculo; switch en `Rules.interes_financiamiento > 0` queda como TODO documentado.
- **Tests:** `cuota_amortizacion(1000, 0.10, 5)` ≈ `263.80`.
- **AC:** test pasa; no se rompe el cálculo actual.

---

### [X] T2.8 — `terceros_totales.py` (§3.9)

- **Objetivo:** matriz subyacente que alimenta el sub-bloque “Terceros” de Totales, **solo con hectáreas de B3**.
- **AC:** golden imagen 10.

#### [X] A2.8.1 — Producción Terceros

- **Lógica:** `ProdT(n, t) = ha_B3_agg(t − n) × ProdTerceros(V, n) / 1000`.
- **Tests:** verificar que ha de B1/B2 **no** contribuyen.
- **AC:** modificar ha de CHAO en B1 no cambia este resultado.

#### [X] A2.8.2 — Ganancia Terceros

- **Lógica:** `GanT(n, t) = ha_B3_agg(t − n) × (GanFOB_Terceros_VentaHF + GanFOB_Terceros_VentaPropia) / 1000`.
- **Tests + AC:** sub-total producción T2728..T3132 = `[—, —, 325, 1_073, 1_869]`; sub-total ganancia = `[5_720, 13_156, 18_304, 23_452, 25_740]` (de UI.png Totales Terceros).

---

### [X] T2.9 — `totales.py` (§3.10)

- **Objetivo:** consolidar Hortifrut y Terceros.
- **AC:** golden contra UI.png sección 5.

#### [X] A2.9.1 — Hortifrut (suma B1 + B2 + B3 + plantines)

- **Lógica:**
  ```
  HF_fruta(t)    = Σ_V (SubProd_B1 + SubProd_B2 + SubProd_B3)
  HF_ganancia(t) = Σ_V (SubGan_B1 + SubGan_B2 + SubGan_B3 + SubGanPlantines_B3)
  ```
- **Tests:** T2728 HF_fruta = `3_250 + 650 + 1_625 = 5_525` ✓; HF_ganancia = `13_000 + 2_600 + 780 + 569 = 16_949` ✓.
- **AC:** todos los valores de la tabla.

#### [X] A2.9.2 — Terceros (solo desde T2.8)

- **Tests:** valores arriba.
- **AC:** coinciden.

---

### [X] T2.10 — Orquestador `recompute.py`

- **Objetivo:** una sola función `recompute(scenario) -> DerivedState`.
- **AC:** un solo test de simulación reproduce TODA la UI.png.

#### [X] A2.10.1 — Función `recompute`

- **Lógica:** orden topológico: `calculos_variedades` → `crecimiento_hf` + `recambio` + `nuevos_terceros` (paralelizables) → `plantines` → `terceros_totales` → `totales`.
- **Tests:** `tests/simulation/test_user_flow_ui_png.py` carga `scenario_ui_png`, llama `recompute`, compara `DerivedState` completo contra los goldens.
- **AC:** test pasa.

#### [X] A2.10.2 — Ordenamiento determinístico

- **Lógica:** ordenar índices de DataFrames con `sort_index()` antes de retornar para garantizar JSON estable.
- **Tests:** `json.dumps(recompute(s).model_dump()) == json.dumps(recompute(s).model_dump())` exacto.
- **AC:** pasa 10 veces seguidas.

---

### [X] T2.11 — Tests property-based (Hypothesis)

- **Objetivo:** invariantes que se cumplen siempre.
- **AC:** Hypothesis con `max_examples=200` no encuentra contraejemplos.

#### [X] A2.11.1 — No-negatividad

- **Hipótesis:** `∀ inputs ≥ 0 ⇒ todos los outputs derivados ≥ 0`.
- **Tests:** estrategia Hypothesis genera escenarios; verifica `all(v ≥ 0 for v in derived.flatten())`.
- **AC:** sin contraejemplos.

#### [X] A2.11.2 — Idempotencia

- **Hipótesis:** `recompute(s) == recompute(s)`.
- **Tests:** comparar hash JSON.
- **AC:** ok.

#### [X] A2.11.3 — Monotonía

- **Hipótesis:** aumentar ha de un sub-proyecto **nunca** decrece la producción total.
- **Tests:** generar dos escenarios `s1` y `s2 = s1 + Δha`. Verificar `totales(s2).hortifrut_fruta[t] >= totales(s1).hortifrut_fruta[t]`.
- **AC:** ok.

#### [X] A2.11.4 — Linealidad (producción/ganancia, NO plantines)

- **Hipótesis:** `recompute(λ·s).produccion == λ·recompute(s).produccion` para `λ > 0`. **Excluir** plantines (truncamiento no es lineal en `Financiamiento`).
- **Tests:** sintetizar y verificar.
- **AC:** ok.

---

## [X] Fase 3 — Persistencia: SQLAlchemy + SQLite dev + Supabase

- **Objetivo:** persistir `ScenarioState` sin acoplarse al motor; mismo código corre con SQLite y Postgres.
- **AC global:** `alembic upgrade head` corre limpio en ambos motores; round-trip `ScenarioState` ok.
- **Referencias:** `description_proyecto.md` §1.3, §1.5; `plan_maestro.md` §Fase 3.

---

### [X] T3.1 — Engine factory dual

- **Objetivo:** elegir pool y dialect según URL.
- **AC:** detección automática del pooler de Supabase.

#### [X] A3.1.1 — `backend/settings.py` con `BaseSettings`

- **Lógica:** Pydantic Settings con `DATABASE_URL`, `DEBOUNCE_MS`, etc.
- **Tests:** importar y leer valores con `.env.example`.
- **AC:** sin secrets en código.

#### [X] A3.1.2 — `backend/db/session.py`

- **Lógica:**
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.pool import NullPool

  def make_engine(url: str):
      if "pooler.supabase.com" in url:
          # Supavisor ya hace pooling — evitar doble pooling (validado vía Context7)
          return create_engine(url, poolclass=NullPool, future=True)
      if url.startswith("sqlite"):
          return create_engine(url, connect_args={"check_same_thread": False}, future=True)
      return create_engine(url, future=True)
  ```
- **Tests:** parametrizar 3 URLs (sqlite, postgres normal, supabase pooler) y verificar atributos del engine.
- **AC:** test pasa.

---

### [X] T3.2 — Modelos ORM

- **Objetivo:** mapear el esquema §1.3 a SQLAlchemy 2.x.
- **AC:** `mypy strict` ok; tablas creadas en SQLite vacío via `Base.metadata.create_all`.

#### [X] A3.2.1 — Tablas `scenario`, `season`, `base_table_*`

- **Lógica:** seguir literal el esquema. Usar `sqlalchemy.JSON` (NO `JSONB`).
- **AC:** importable.

#### [X] A3.2.2 — `variety`, `variety_param`

- **Lógica:** `UNIQUE(variety_id, plant_year)`; FK a `scenario`.
- **AC:** test de integridad: insertar duplicado falla.

#### [X] A3.2.3 — `rules`, `new_project_group`, `new_project_subrow`, `new_project_ha`

- **Lógica:** `rules` 1:1 con `scenario`. `new_project_ha` sparse (solo celdas con valor).
- **AC:** modelo refleja el dominio.

#### [X] A3.2.4 — `audit_log` con `payload JSON`

- **AC:** insertar y leer un dict arbitrario funciona en ambos motores.

---

### [X] T3.3 — Alembic init + migración inicial

- **Objetivo:** migraciones versionadas.
- **AC:** `alembic upgrade head` ok en SQLite y Postgres vacíos.

#### [X] A3.3.1 — `alembic init alembic`

- **Proceso:** después, editar `alembic/env.py` para leer `DATABASE_URL` desde `settings` y usar `Base.metadata`.
- **AC:** archivo `env.py` no contiene URLs hardcoded.

#### [X] A3.3.2 — Migración `0001_initial`

- **Proceso:** `alembic revision --autogenerate -m "initial"`. Revisar diff antes de commitear.
- **Tests:** levantar SQLite vacío, correr migración, verificar tablas con `inspect(engine).get_table_names()`.
- **AC:** todas las tablas existen.

---

### [X] T3.4 — Seeds default

- **Objetivo:** datos iniciales para arrancar.
- **AC:** `python scripts/seed_dev_db.py` deja un escenario canónico cargado.

#### [X] A3.4.1 — `backend/db/seeds.py`

- **Lógica:** Tabla Base de imagen 1 + Reglas defaults (§3.3).
- **AC:** función `apply_defaults(session, scenario_id)` insertable.

#### [X] A3.4.2 — `scripts/seed_dev_db.py`

- **Lógica:** crea escenario `"UI.png demo"` + V1 + las 5 celdas de ha + corre `recompute` y guarda nada (es solo demo).
- **AC:** tras correr, `sqlite3 var/app.db ".tables"` lista las tablas pobladas.

---

### [X] T3.5 — Repositorios

- **Objetivo:** abstraer SQL detrás de funciones que aceptan/devuelven Pydantic.
- **AC:** round-trip `ScenarioState` → DB → `ScenarioState` es bit-a-bit igual.

#### [X] A3.5.1 — `ScenarioRepo`

- **Lógica:** `create`, `get_by_id`, `update`, `delete`, `list`. Lee `ScenarioState` desde DB y viceversa.
- **Tests:** `tests/integration/test_repos.py` con SQLite en memoria.
- **AC:** ok.

#### [X] A3.5.2 — `VarietyRepo`, `RulesRepo`, `NewProjectsRepo`

- **Lógica:** análogos.
- **AC:** tests por repo.

---

### [X] T3.6 — Audit log

#### [X] A3.6.1 — Decorador `@audited`

- **Lógica:**
  ```python
  def audited(entity: str):
      def deco(fn):
          def wrap(self, *a, **kw):
              before = fn(self, *a, **kw)
              self.session.add(AuditLog(entity=entity, payload=...))
              return before
          return wrap
      return deco
  ```
- **AC:** un `update_variety_params` produce 1 row en `audit_log`.

---

## [X] Fase 4 — API Starlette

- **Objetivo:** exponer CRUD + recompute + export.
- **AC global:** OpenAPI generada documenta todos los endpoints; tests de integración pasan.

---

### [X] T4.1 — Schemas Pydantic para request/response

#### [X] A4.1.1 — DTOs separados de modelos de dominio

- **Lógica:** evitar exponer campos internos (ej. `id`, `created_at`).
- **AC:** schemas en `backend/api/schemas.py`.

---

### [X] T4.2 — Rutas

- **AC:** tabla de endpoints documentada y tests para cada uno.

#### [X] A4.2.1 — `GET/POST /api/scenarios`

- **Tests:** crear escenario, listarlo.
- **AC:** 201 al crear, 200 al listar.

#### [X] A4.2.2 — `GET/PUT/DELETE /api/scenarios/{id}`

- **Tests:** roundtrip CRUD.
- **AC:** 404 si no existe.

#### [X] A4.2.3 — Variedades

- **Endpoints:** `POST /api/scenarios/{id}/varieties`, `PUT /api/varieties/{id}/params`, `DELETE /api/varieties/{id}`.
- **AC:** validación Pydantic 422 si falta `Año k`.

#### [X] A4.2.4 — Rules

- **Endpoints:** `GET/PUT /api/scenarios/{id}/rules`.
- **AC:** defaults se devuelven en escenario nuevo.

#### [X] A4.2.5 — Celdas de ha

- **Endpoints:** `PUT /api/scenarios/{id}/new-projects` (upsert).
- **AC:** crear/actualizar/poner en 0.

---

### [X] T4.3 — Recompute endpoint

#### [X] A4.3.1 — `POST /api/scenarios/{id}/recompute`

- **Lógica:** lee desde DB → construye `ScenarioState` → llama `recompute()` → retorna `DerivedState` como JSON.
- **Tests:** `tests/integration/test_api_recompute.py` envía escenario UI.png, compara JSON con goldens.
- **AC:** tolerancia `abs ≤ 1`.

---

### [X] T4.4 — Export XLSX

#### [X] A4.4.1 — `GET /api/scenarios/{id}/export.xlsx`

- **Lógica:** xlsxwriter, 5 hojas (una por sección UI), formatos `#,##0`. Headers ciruela/verde según UI.png.
- **Tests:** abrir el XLSX con `openpyxl` y verificar una celda por sección.
- **AC:** archivo descargable, abre en Excel sin warning de corrupción.

---

### [X] T4.5 — Manejo de errores

#### [X] A4.5.1 — Middleware de excepciones

- **Lógica:**
  - `pydantic.ValidationError` → 422
  - Errores de dominio (`DomainError`) → 400
  - `IntegrityError` → 409
  - resto → 500 con `request_id`
- **Tests:** un test por código.
- **AC:** tests pasan.

---

## [X] Fase 5 — Aplicación Shiny

- **Objetivo:** UI reactiva que refleja UI.png consumiendo la API.
- **AC global:** screenshot ≈ UI.png; debounce 1.5 s funciona; cambios persisten vía API.
- **Referencias:** `description_proyecto.md` §2 (wireframe ASCII).

---

### [X] T5.1 — Layout maestro y estilos

#### [X] A5.1.1 — `backend/shiny_app/app.py` con 5 secciones

- **Proceso:** `ui.page_fluid(...)` con 5 `ui.card` o `ui.layout_columns` siguiendo el wireframe.
- **AC:** revisión visual.

#### [X] A5.1.2 — `styles.css` con tokens

- **Lógica:** `:root { --color-ciruela:#E7B6D1; --color-verde:#0E7C3E }` + clases utilitarias.
- **AC:** clases reutilizables desde los módulos.

---

### [X] T5.2 — Bridge reactivo `state.py`

#### [X] A5.2.1 — `reactive.value[ScenarioState]` central

- **Lógica:** módulo `state.py` con session factory inyectada desde lifespan. Expone load/save directo sin HTTP (Shiny y API comparten mismo proceso). Cálculo central vía `@reactive.calc` en server.
- **Tests:** E2E (F8) confirma persistencia tras reload.
- **AC:** funciona.

---

### [X] T5.3 — Helper de debounce

#### [X] A5.3.1 — `debounce(input_value, ms=1500)`

- **Lógica:** implementado en `reactive_helpers.py` con `reactive.invalidate_later` + check de tiempo transcurrido. Módulo `new_projects` usa patrón de debounce de 1.5 s con `_collect_ha` + `_debounced_flush`.
- **Tests:** E2E (F8) cubre debounce funcional.
- **AC:** test pasa.

---

### [X] T5.4 — Módulo `base_table.py` (Sección 1)

#### [X] A5.4.1 — Tabla editable

- **Lógica:** tabla con filas de proyecto (solo-lectura desde DB) + fila variación con inputs numéricos editables.
- **AC:** edición persiste vía API.

#### [X] A5.4.2 — Botón `[Confirmar Base]`

- **Lógica:** botón que bloquea la sección (modo solo-lectura). Estado gestionado con `reactive.value` local.
- **Tests E2E:** intentar editar después de confirmar → bloqueado.
- **AC:** ok.

---

### [X] T5.5 — Módulo `varieties_panel.py` (Sección 2)

#### [X] A5.5.1 — `[+ Agregar variedad]`

- **Lógica:** botón activa modo "new" con formulario; valida nombre no vacío; rechaza nombres duplicados (409 de DB).
- **AC:** rechaza nombres vacíos.

#### [X] A5.5.2 — Tabla Variable × Año plegable

- **Lógica:** `ui.accordion` en modo vista; formulario de edición en modo "edit".
- **AC:** revisión visual.

#### [X] A5.5.3 — `[Hecho]` con validación estricta

- **Lógica:** `_collect_params` valida 7×4 inputs no nulos; retorna None si hay vacíos.
- **AC:** test E2E.

---

### [X] T5.6 — Módulo `rules_panel.py` (Sección 3)

#### [X] A5.6.1 — 4 campos editables verdes

- **Lógica:** 4 `ui.input_numeric` con clase `rules-input` (color verde via CSS). Botón "Guardar Reglas" llama `save_rules()` + `reload_fn()`.
- **Tests:** cambiar `financiamiento_anios` de 5 a 3 dispara recompute y plantines T3031/T3132 caen a 0.
- **AC:** valor reflejado en sección 4 tras debounce.

---

### [X] T5.7 — Módulo `new_projects.py` (Sección 4)

#### [X] A5.7.1 — Filtro variedad

- **Lógica:** `ui.input_select` con variedades del escenario activo.
- **AC:** cambiar variedad recarga la grilla.

#### [X] A5.7.2 — Grilla con celdas ciruela editables

- **Lógica:** 3 bloques × sub-proyectos × 6 seasons; inputs con clase `ha-input` (fondo ciruela via CSS). Debounce 1.5 s via `_collect_ha` + `_debounced_flush`.
- **Tests E2E:** introducir CHAO=250 en T2627 → tras 1.5 s, subtotales se actualizan.
- **AC:** ok.

#### [X] A5.7.3 — Sub-totales server-side

- **Lógica:** leen `derived['crecimiento'][variety]`, `derived['recambio'][variety]`, `derived['nuevos_terceros'][variety]`, `derived['plantines'][variety]`. No calculan en JS.
- **AC:** consistencia con goldens.

---

### [X] T5.8 — Módulo `totals.py` (Sección 5)

#### [X] A5.8.1 — Tabla read-only de 4 filas

- **Lógica:** lee `derived['totales']['hf_fruta']`, `hf_ganancia`, `terceros_fruta`, `terceros_ganancia`. Tabla HTML solo-lectura.
- **AC:** valores coinciden con goldens (test E2E).

---

### [X] T5.9 — Bloqueos UX

#### [X] A5.9.1 — Sección 4 deshabilitada sin variedades

- **Lógica:** `new_projects_server` muestra mensaje con `title` tooltip cuando `state.varieties` está vacío.
- **AC:** test E2E negativo.

#### [X] A5.9.2 — Modal al eliminar variedad con ha

- **Lógica:** `_pending_delete` muestra warning inline; botón “Confirmar eliminación” ejecuta cascade. `variety_has_ha()` advierte si hay ha asignadas.
- **AC:** test E2E.

---

## [X] Fase 6 — Integración Starlette ↔ Shiny ↔ estáticos

- **Objetivo:** un solo proceso atiende API + Shiny + estáticos.
- **AC global:** `localhost:8000/` carga el shell Astro; `localhost:8000/shiny/` la app reactiva; `/api/*` los endpoints.

---

### [X] T6.1 — Orden de mounts en `app.py`

#### [X] A6.1.1 — Verificar orden

- **Lógica:** rutas API → `/shiny` → `/` (StaticFiles **siempre al final**, ver `plan_replication.md` §4.3).
- **Tests:** los 3 cURLs.
- **AC:** todos 200.

---

### [X] T6.2 — Pipeline build Astro → estáticos

#### [X] A6.2.1 — `scripts/build.ps1`

- **Lógica:**
  ```powershell
  cd frontend; pnpm run build; cd ..
  uv run python scripts/inline_js.py
  if (-not (Test-Path backend\static)) { New-Item -ItemType Directory backend\static -Force }
  Copy-Item -Path frontend\dist\* -Destination backend\static\ -Recurse -Force
  ```
- **AC:** tras correr, `localhost:8000/` muestra el shell Astro.

#### [X] A6.2.2 — `scripts/inline_js.py`

- **Lógica:** inyectar JS de `dist/_astro/*.js` inline en `index.html` y corregir rutas de favicon. Patrón validado en `plan_replication.md` §5.
- **AC:** `index.html` no referencia recursos en `/_astro/`.

---

### [X] T6.3 — Auditoría rutas relativas

#### [X] A6.3.1 — Grep de rutas absolutas

- **Proceso:** `grep -r '"/api' frontend/src`; `grep -r '"/shiny' frontend/src`. Deben estar como `./api` o `./shiny`.
- **AC:** sin matches absolutos.

---

## [X] Fase 7 — Frontend Astro

- **Objetivo:** shell estático con header + iframe Shiny.
- **AC global:** Lighthouse Performance ≥ 90; revisión visual ok.

---

### [X] T7.1 — `index.astro`

#### [X] A7.1.1 — Layout SPA single-page

- **Lógica:** header arriba; iframe `src=”./shiny/”` ocupa el resto del viewport con `height: calc(100vh - 64px)`.
- **AC:** Lighthouse ≥ 90.

---

### [X] T7.2 — Tokens Tailwind

#### [X] A7.2.1 — `tailwind.config.cjs`

- **Lógica:** colores `ciruela` y `verde` definidos como tokens.
- **AC:** `bg-ciruela`, `text-verde` funcionan.

---

### [X] T7.3 — Componentes mínimos

#### [X] A7.3.1 — `Header.astro`

- **Contenido:** logo, título (“Business Planning 2026 — Perú”), placeholder de usuario.
- **AC:** se muestra.

#### [X] A7.3.2 — `ScenarioSwitcher.astro`

- **Lógica:** dropdown vacío por ahora; conectará a `/api/scenarios` en Fase 10.
- **AC:** componente importable.

---

## [X] Fase 8 — Tests E2E

- **Objetivo:** simular el flujo real del usuario contra el sistema integrado.
- **AC global:** test del flujo completo de UI.png pasa headless.

---

### [X] T8.1 — Setup Playwright

#### [X] A8.1.1 — `tests/e2e/conftest.py`

- **Lógica:** fixture `page` que abre `localhost:8000/` con browser efímero.
- **Proceso:** `uv run playwright install chromium`.
- **AC:** test mínimo abre la página.

---

### [X] T8.2 — Flujo completo UI.png

#### [X] A8.2.1 — `test_playwright_flow.py`

- **Proceso:**
  1. Crear escenario.
  2. Rellenar Tabla Base (imagen 1).
  3. `[Confirmar Base]`.
  4. Crear V1 con datos de imagen 2; `[Hecho]`.
  5. Dejar Reglas default.
  6. Editar las 5 ha de UI.png en sección 4.
  7. `page.wait_for_timeout(1800)` (debounce + margen).
  8. Aserciones: leer textos de sub-totales y totales, comparar contra goldens.
- **AC:** todas las aserciones pasan.

---

### [X] T8.3 — Recarga y persistencia

#### [X] A8.3.1 — Test de reload

- **Proceso:** tras paso 6, `page.reload()`; verificar que los valores siguen ahí; verificar que NO hay error 404 (patrón SPA, ver `plan_replication.md` §3).
- **AC:** ok.

---

## [X] Fase 9 — Documentación

- **Objetivo:** README + ejecucion.md raíz que permitan a un dev nuevo levantar y desplegar.
- **AC global:** dev nuevo levanta dev en < 15 min y despliega a ShinyApps.io en < 1 h.

---

### [X] T9.1 — `README.md` raíz

#### [X] A9.1.1 — Contenido ejecutivo

- **Secciones:**
  - Qué hace (link a `description_proyecto.md`).
  - Stack (link a `plan_maestro.md` §Stack tecnológico).
  - Quick start (3 comandos: `uv sync`, `cp .env.example .env`, `./scripts/dev.ps1`).
  - Tests (`uv run pytest`).
  - Despliegue (link a `ejecucion.md`).
- **AC:** un dev sigue solo el README y llega a `localhost:8000/`.

---

### [X] T9.2 — `ejecucion.md` raíz

#### [X] A9.2.1 — Réplica de `docs/doc_guia/ejecucion.md` adaptada

- **Secciones (siguiendo plantilla):**
  - §1 Requisitos previos.
  - §2 Instalación local (uv + pnpm).
  - §3 Ejecución dev (`dev.ps1` + manual).
  - §4 Build prod (frontend → static).
  - §5 Despliegue ShinyApps.io (rsconnect + `--app-id`).
  - §6 Troubleshooting (404 recarga, rutas absolutas, WS, numpy/3.13).
  - §7 Tests (`pytest unit/`, `pytest golden/`, `pytest e2e/`).
- **AC:** un dev despliega en < 1 h.

---

### [X] T9.3 — Diagramas

#### [X] A9.3.1 — Render Mermaid → SVG

- **Proceso:** exportar el diagrama de `description_proyecto.md` §1.2 a `docs/diagrams/flujo_reactivo.svg`. Agregar diagrama de despliegue.
- **AC:** SVGs renderizan en GitHub web.

---

### [X] T9.4 — Estandarización de Documentación de Código

#### [X] A9.4.1 — Docstrings en Suite de Tests (SKILL.md)

- **Objetivo:** Profesionalizar la documentación técnica de la suite de pruebas siguiendo los estándares de arquitectura del proyecto.
- **AC:** 100% de los archivos `.py` en `tests/` cuentan con encabezados de módulo, descripción de acciones principales y ejemplos de ejecución en formato Google Style (Español).

---

## [ ] Fase 10 — Despliegue (Supabase + ShinyApps.io)

- **Objetivo:** app accesible online con datos en Supabase Postgres.
- **AC global:** URL pública funcional con todos los flujos validados.

---

### [ ] T10.1 — Provisión Supabase

#### [ ] A10.1.1 — Crear proyecto Supabase free tier

- **Proceso:** UI Supabase → New project → región más cercana.
- **AC:** dashboard accesible.

#### [ ] A10.1.2 — Copiar transaction pooler URL (port 6543)

- **Lógica:** Settings → Database → Connection pooling → Transaction mode.
- **Formato esperado:** `postgresql+psycopg://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:6543/postgres`.
- **AC:** URL guardada en password manager.

#### [ ] A10.1.3 — `alembic upgrade head` contra Supabase

- **Proceso:** setear `DATABASE_URL` en `.env`, `uv run alembic upgrade head`.
- **AC:** tablas creadas; verificar en Table Editor de Supabase.

---

### [ ] T10.2 — Adaptar `session.py` para Supabase

- **Cubierto:** A3.1.2 ya tiene la detección. Verificar funciona con la URL real.

#### [ ] A10.2.1 — Smoke test contra Supabase

- **Tests:** `uv run pytest tests/integration -k supabase --use-supabase` (flag personalizado).
- **AC:** repos funcionan contra Postgres real.

---

### [ ] T10.3 — `.rscignore` + `requirements.txt`

#### [ ] A10.3.1 — Generar `requirements.txt`

- **Proceso:** `uv pip compile pyproject.toml -o requirements.txt`. Revisar manualmente y NO incluir dev deps.
- **AC:** archivo presente y sin packages dev.

#### [ ] A10.3.2 — Validar `.rscignore`

- **Proceso:** `rsconnect deploy --dry-run` (con cuenta configurada).
- **AC:** bundle final no contiene `frontend/`, `node_modules/`, `tests/`, `docs/`, `scripts/`.

---

### [ ] T10.4 — Primer deploy

#### [ ] A10.4.1 — Registrar cuenta

- **Proceso:**
  ```powershell
  uv run python -c "from rsconnect.main import cli; cli()" add `
      --account $env:rsconnect_usuario --name $env:rsconnect_name `
      --token $env:rsconnect_token --secret $env:rsconnect_secret
  ```
- **AC:** `rsconnect list-accounts` muestra la cuenta.

#### [ ] A10.4.2 — Deploy inicial

- **Proceso:**
  ```powershell
  uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . `
      --entrypoint app:app --name $env:rsconnect_usuario `
      --title "HF-Breeding-Planner" --new
  ```
- **AC:** URL pública accesible.

---

### [ ] T10.5 — Redeploy

#### [ ] A10.5.1 — Documentar `--app-id`

- **Proceso:** registrar el `app-id` que devuelve el primer deploy en `ejecucion.md`. Redeploys:
  ```powershell
  uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . `
      --entrypoint app:app --name $env:rsconnect_usuario --app-id <ID>
  ```
- **AC:** cambio trivial sube en < 5 min.

---

### [ ] T10.6 — Verificación post-deploy

#### [ ] A10.6.1 — Checklist

- **Checklist** (basado en `doc_guia/ejecucion.md` §5.5):
  - [ ] URL pública abre sin errores.
  - [ ] Iframe Shiny carga.
  - [ ] CRUD escenarios funciona contra Supabase.
  - [ ] Subtotales reproducen UI.png.
  - [ ] Recarga **NO** da 404 (patrón SPA).
  - [ ] Export XLSX descargable.
- **AC:** los 6 items en verde.

---

## Apéndice — Mapa de tests por archivo

| Archivo de logic                          | Test unitario                              | Test golden                                             |
| ----------------------------------------- | ------------------------------------------ | ------------------------------------------------------- |
| `logic/calculos_variedades.py`            | `tests/unit/test_calculos_variedades.py`   | (cubierto indirecto en golden de bloques)               |
| `logic/lag_matrix.py`                     | `tests/unit/test_lag_matrix.py`            | —                                                       |
| `logic/crecimiento_hf.py`                 | `tests/unit/test_crecimiento_hf.py`        | `tests/golden/test_golden_imagen7_crecimiento.py`       |
| `logic/recambio.py`                       | `tests/unit/test_recambio.py`              | `tests/golden/test_golden_imagen8_recambio.py`          |
| `logic/nuevos_terceros.py`                | `tests/unit/test_nuevos_terceros.py`       | `tests/golden/test_golden_imagen9_nuevos_terceros.py`   |
| `logic/plantines.py`                      | `tests/unit/test_plantines.py`             | (cubierto en `test_golden_imagen9_*`)                   |
| `logic/terceros_totales.py`               | `tests/unit/test_terceros_totales.py`      | `tests/golden/test_golden_imagen10_terceros_totales.py` |
| `logic/totales.py`                        | `tests/unit/test_totales.py`               | `tests/golden/test_golden_ui_totales.py`                |
| `logic/recompute.py`                      | —                                          | `tests/simulation/test_user_flow_ui_png.py`             |

---

## Apéndice — Convención de tolerancia para goldens

- **Enteros del UI:** `abs(actual − expected) ≤ 1` (acomoda redondeo bancario).
- **Floats internos:** `pytest.approx(expected, rel=1e-3, abs=1e-6)`.
- **Plantines (con división):** misma tolerancia entera; los valores `568.75` ⇒ `569` son aceptables.

---

> **Próximo paso recomendado.** Comenzar por Fase 0 (`T0.1 → T0.6`) marcando cada Acción `[/]` al iniciarla y `[X]` al cumplir su AC. Cuando todas las Acciones de una Tarea estén `[X]`, marcar la Tarea `[X]` y validar el AC de Tarea. Cuando todas las Tareas de una Fase estén `[X]`, marcar la Fase `[X]`.
