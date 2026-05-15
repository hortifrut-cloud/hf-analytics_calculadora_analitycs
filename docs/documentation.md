# Documentación Técnica — HF Breeding Planner

> **Audiencia:** Tech leads, desarrolladores senior que necesitan entender el sistema en profundidad para diagnosticar problemas, extender funcionalidad o hacer onboarding.
>
> Para diagramas y visión ejecutiva → [`docs/architect/architecture.md`](architect/architecture.md)
> Para especificación funcional y fórmulas → [`docs/description_proyecto.md`](description_proyecto.md)

---

## Índice

1. [Mapa del repositorio](#1-mapa-del-repositorio)
2. [Entrypoint y ciclo de vida](#2-entrypoint-y-ciclo-de-vida)
3. [Capa de dominio](#3-capa-de-dominio)
4. [Motor de cálculo](#4-motor-de-cálculo)
5. [Capa de persistencia](#5-capa-de-persistencia)
6. [Sistema reactivo Shiny](#6-sistema-reactivo-shiny)
7. [API REST](#7-api-rest)
8. [Frontend Astro](#8-frontend-astro)
9. [Patrones críticos de rendimiento](#9-patrones-críticos-de-rendimiento)
10. [Variables de entorno](#10-variables-de-entorno)
11. [Tests](#11-tests)
12. [Guía de diagnóstico](#12-guía-de-diagnóstico)
13. [Problemas conocidos y soluciones aplicadas](#13-problemas-conocidos-y-soluciones-aplicadas)

---

## 1. Mapa del repositorio

```
app.py                          ← Entrypoint Starlette (ShinyApps: app:app)
backend/
  settings.py                   ← Pydantic Settings (carga .env)
  domain/
    enums.py                    ← Productor, BloqueKind, SeasonCode, PlantYear
    inputs.py                   ← ScenarioState, Variety, Rules, NewProjectCell (Pydantic, frozen)
    derived.py                  ← DerivedState, MatrizSubyacente, Subtotales, Totales
  logic/
    calculos_variedades.py      ← Productividad/ganancia por variedad × año de planta
    lag_matrix.py               ← build_lag_matrix: shift temporal de hectáreas
    crecimiento_hf.py           ← Bloque B1: CHAO/OLMOS internos HF
    recambio.py                 ← Bloque B2: recambio varietal
    nuevos_terceros.py          ← Bloque B3: proyectos con terceros
    plantines.py                ← Ganancia plantines con tope por financiamiento
    terceros_totales.py         ← Producción y ganancia de productores externos
    totales.py                  ← Consolidado HF + Terceros
    recompute.py                ← Orquestador: ScenarioState → DerivedState
  db/
    models.py                   ← ORM SQLAlchemy 2.x (Mapped[...])
    repos.py                    ← ScenarioRepo, RulesRepo, AuditRepo
    session.py                  ← Engine factory dual (SQLite/Supabase), fixes psycopg3
    seeds.py                    ← apply_defaults() para escenario inicial
  api/
    routes.py                   ← Rutas REST montadas en /api
    schemas.py                  ← DTOs Pydantic para request/response
  shiny_app/
    app.py                      ← App Shiny: layout, server, reactive core
    state.py                    ← Bridge DB↔Shiny: caché, repos, batch upserts
    styles.css                  ← Sistema de diseño (variables CSS + componentes)
    modules/
      base_table.py             ← Sección 1: Tabla Base (colapsable)
      varieties_panel.py        ← Sección 2: Variedades agronómicas
      rules_panel.py            ← Sección 3: Reglas / snapshot KPI
      new_projects.py           ← Sección 4: Nuevos proyectos + delta badges
      totals.py                 ← Sección 5: Totales + delta badges
frontend/
  src/
    pages/index.astro           ← Shell SPA: header + iframe /shiny/
    components/Header.astro
    styles/global.css           ← Tokens Tailwind (--color-ciruela, --color-verde)
  astro.config.mjs              ← Output static, inlineStylesheets always, proxy dev
scripts/
  dev.ps1                       ← Arranca uvicorn :8000 + Astro :4321 en paralelo
  build.ps1                     ← Astro build → inline_js.py → backend/static/
  inline_js.py                  ← Inyecta /_astro/*.js en index.html (req. ShinyApps.io)
  seed_dev_db.py                ← Siembra escenario canónico (lee DATABASE_URL de .env)
tests/
  unit/                         ← Lógica pura (calculos_variedades, bloques, totales)
  golden/                       ← vs. docs/image/imagen{7..10}.csv (tolerancia abs≤1)
  integration/                  ← API + DB SQLite en memoria
  property/                     ← Hypothesis: no-negatividad, idempotencia, monotonía, linealidad
  simulation/                   ← test_user_flow_ui_png.py: reproduce UI.png completo
  e2e/                          ← Playwright: flujo completo headless
```

---

## 2. Entrypoint y ciclo de vida

**Archivo:** `app.py` (raíz del repo)

El entrypoint Starlette configura el ASGI app con tres preocupaciones: lifespan (DB init), rutas, y manejo de errores.

### Lifespan

```python
@asynccontextmanager
async def lifespan(app):
    engine, session_factory, owned = _init_engine_and_session()
    if "sqlite" in str(settings.database_url):
        Base.metadata.create_all(engine)   # solo SQLite — Postgres usa Alembic
    shiny_state.configure(session_factory)
    yield
    if owned:
        engine.dispose()
```

El flag `owned` evita que el lifespan dispose un engine inyectado por tests. Si `DATABASE_URL` contiene `pooler.supabase.com`, el engine se crea con `NullPool` y `prepare_threshold=0`.

**Regla crítica:** `StaticFiles` siempre se monta último. Cualquier route que se monte después de `StaticFiles` nunca se alcanzará — Starlette evalúa las rutas en orden.

### Orden de rutas

```python
routes = [
    Route("/api/status", status_endpoint),
    Mount("/api", routes=api_routes),
    Mount("/shiny", app=shiny_app),
    Mount("/", app=StaticFiles(directory="backend/static", html=True)),  # ← siempre último
]
```

### Manejo de errores

| Excepción | Código HTTP | Código de aplicación |
|---|---|---|
| `DomainError` | 400 | Error de validación de negocio |
| `pydantic.ValidationError` | 422 | Input inválido en endpoint REST |
| `sqlalchemy.exc.IntegrityError` | 409 | Duplicado en DB (nombre variedad, etc.) |
| Cualquier otra | 500 | Error inesperado con `request_id` |

---

## 3. Capa de dominio

**Directorio:** `backend/domain/`

Todos los modelos son Pydantic v2 con `frozen=True` (inmutables). Esto habilita:
- Hash y uso como claves de dict.
- `model_copy(update={...})` para crear versiones modificadas sin mutar el original.
- Thread-safety natural en el caché en memoria.

### Modelos principales

**`ScenarioState`** — estado completo de un escenario:
- `name`, `country`
- `base_table: BaseTable` — proyectos + variación
- `varieties: list[Variety]` — con 7 filas de parámetros cada una
- `rules: Rules` — 4 parámetros globales
- `new_project_cells: list[NewProjectCell]` — sparse: solo celdas con valor

**`DerivedState`** — output del motor (no se persiste):
- Estructurado como `dict` jerárquico: `{bloque: {variety: {sub: {season: float}}}}`
- Serializable a JSON para respuestas REST y para el snapshot de KPI delta.

### Validadores cross-field

- `Variety._check_years`: exige exactamente los 7 plant_years `{1..7}`.
- `ScenarioState._check_variety_refs`: verifica que `cell.variety_name` existe en `varieties`.

---

## 4. Motor de cálculo

**Directorio:** `backend/logic/`

**Invariante crítico:** ningún archivo en `logic/` puede hacer I/O. No SQLAlchemy, no archivos, no HTTP. Solo funciones puras que operan sobre `ScenarioState` y devuelven estructuras de datos.

### Pipeline topológico (orden fijo)

```
ScenarioState
    │
    ▼
calculos_variedades          → dict[(variety, productor, plant_year)] = {produccion, ganancia}
    │
    ├──► crecimiento_hf      → {variety: {produccion: {season: float}, ganancia: {season: float}}}
    ├──► recambio             → misma estructura
    └──► nuevos_terceros      → idem
             │
             ├──► plantines   → {variety: {season: float}} (truncado por financiamiento_anios)
             └──► terceros_totales → {produccion, ganancia} solo para productores externos
                      │
                      ▼
                  totales     → {hf_fruta, hf_ganancia, terceros_fruta, terceros_ganancia}
```

### Mecanismo de lag temporal (`lag_matrix.py`)

La relación fundamental del negocio es: *la producción en temporada `t` de una planta en año `n` depende de las hectáreas sembradas en `t-n`*.

```python
def build_lag_matrix(ha_by_season, max_plant_year, seasons):
    base = pd.Series(ha_by_season).reindex(seasons).fillna(0.0)
    return pd.DataFrame(
        {n: base.shift(n).fillna(0.0).values for n in range(1, max_plant_year + 1)},
        index=seasons
    ).T  # filas: plant_year, columnas: season
```

`M[n, t]` = hectáreas sembradas en `t-n`. La producción se calcula como `M × params[n]`, sumando sobre años.

### Unidades y conversión

Todo el cálculo intermedio opera en `Kg/planta × planta/ha = Kg/ha`. La conversión a toneladas ocurre al final de cada bloque (`÷ 1000`). Los valores monetarios están en miles de USD, no en USD.

---

## 5. Capa de persistencia

**Archivos:** `backend/db/models.py`, `repos.py`, `session.py`

### Engine factory (`session.py`)

```python
def make_engine(url: str) -> Engine:
    if "pooler.supabase.com" in url:
        return create_engine(url, poolclass=NullPool,
                             connect_args=_supabase_connect_args(url))
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)
```

`_supabase_connect_args()` pre-resuelve el hostname a IP para evitar el DNS lookup síncrono de psycopg3 en el event loop de asyncio (bug confirmado en psycopg3 3.3.x con Python 3.13). También registra un evento `connect` que ejecuta `DEALLOCATE ALL` y setea `prepare_threshold=0`.

### Repositorios (`repos.py`)

`ScenarioRepo.get(scenario_id)` usa `selectinload` en 6 relaciones para cargar el escenario completo en un solo round-trip (evita el problema N+1):

```python
session.query(Scenario).options(
    selectinload(Scenario.seasons),
    selectinload(Scenario.base_table_rows).selectinload(BaseTableRow.values),
    selectinload(Scenario.base_table_variation),
    selectinload(Scenario.varieties).selectinload(Variety.params),
    selectinload(Scenario.rules),
    selectinload(Scenario.new_project_groups)
        .selectinload(NewProjectGroup.subrows)
        .selectinload(NewProjectSubrow.ha_cells),
).filter_by(id=scenario_id).first()
```

La conversión ORM ↔ Pydantic ocurre dentro del repo. El resto del sistema solo ve modelos Pydantic.

### Caché en memoria (`shiny_app/state.py`)

```python
_state_cache: dict[int, ScenarioState] = {}
```

Reglas del caché:
- **Lee:** `load_scenario()` → cache-first; solo va a DB en cache miss.
- **Escribe reglas:** `save_rules()` → DB write + `_cache_set(id, cached.model_copy(update={"rules": rules}))`. No re-lee DB.
- **Escribe ha:** `batch_upsert_ha_cells()` → DB write en batch + actualiza `new_project_cells` en el caché en-place.
- **Crea/edita/elimina variedad:** `create_variety()`, `update_variety_params()`, `delete_variety()` → `_cache_invalidate(id)`. La reconstrucción completa de `varieties` en memoria es compleja; se prefiere re-leer desde DB.

**Importante:** El `scenario_id` se debe capturar dentro del bloque `with _session() as s:` antes de que la sesión se cierre, porque los atributos ORM lazy no son accesibles fuera de la sesión.

### Batch upsert de hectáreas (`batch_upsert_ha_cells`)

Una sola sesión de DB para N celdas:
1. Carga `season_map`, `variety_map`, `group_map` — 3 queries.
2. Crea grupos faltantes si es necesario.
3. Carga `subrow_map` para los grupos relevantes — 1 query con `IN`.
4. Crea subrows faltantes.
5. Carga `ha_map` para los subrows relevantes — 1 query con `IN`.
6. Upsert de cada celda sin queries adicionales.
7. `commit()`.
8. Actualiza caché en-place.

Total: ~5-6 queries para cualquier número de celdas (era `N × 8` queries antes).

---

## 6. Sistema reactivo Shiny

**Archivo principal:** `backend/shiny_app/app.py`

### Grafo reactivo central

```
_reload_counter (reactive.Value[int])
    │
    ▼
current_state() (@reactive.calc)       ← load_scenario(scenario_id) desde caché
    │
    ▼
current_derived() (@reactive.calc)     ← recompute(state) con Pandas/NumPy
    │
    ├──► base_table_content (@render.ui)
    ├──► varieties_panel_content (@render.ui)
    ├──► rules_form (@render.ui)
    ├──► new_projects_content (@render.ui)
    └──► totals_table (@render.ui)
```

`trigger_reload()` = `_reload_counter.set(n+1)` → invalida `current_state()` → invalida `current_derived()` → re-renderiza todos los módulos dependientes.

### Debounce en Sección 4

El debounce no usa `reactive.poll` ni helpers externos; usa `reactive.invalidate_later` + timestamp manual:

```python
@reactive.effect
def _debounced_flush():
    reactive.invalidate_later(1.5)
    p = _pending.get()
    if not p or time.monotonic() - p["t"] < 1.45:
        return
    # procesar cambios...
```

`_collect_ha` captura todos los valores del formulario y los pone en `_pending` con timestamp. `_debounced_flush` se auto-invalida cada 1.5 s, pero solo procesa cuando han pasado 1.45 s desde el último cambio. Esto es más eficiente que un timer externo porque Shiny se encarga de la scheduling.

### Snapshot para KPI delta

```
"Guardar Reglas" click
    │
    ├── snapshot_fn()     → _snapshot_derived = current_derived() (valores ANTES del cambio)
    ├── save_rules()      → DB write + cache update
    └── reload_fn()       → current_derived() se recalcula con nuevas reglas
                                    │
                                    ▼
                        new_projects_content(derived=NUEVO, prev=SNAPSHOT)
                        totals_table(derived=NUEVO, prev=SNAPSHOT)
                            → delta = NUEVO - SNAPSHOT → badges ▲/▼
```

El snapshot se captura de forma síncrona dentro del `@reactive.effect` de `_on_save`, antes de que `save_rules` actualice el caché. Shiny batea las actualizaciones de `reactive.Value` hasta el final del effect, por lo que solo hay un re-render con el estado final correcto.

### Módulos UI

Cada módulo es un par `(module.ui, module.server)` con namespace aislado. La comunicación entre módulos ocurre exclusivamente a través de los callables inyectados en el server:

| Callable | Tipo | Propósito |
|---|---|---|
| `state_fn` | `() → ScenarioState \| None` | Lee el estado actual desde caché |
| `derived_fn` | `() → dict \| None` | Lee el DerivedState calculado |
| `reload_fn` | `() → None` | Dispara recálculo reactivo |
| `scenario_id_rv` | `reactive.Value[int]` | ID del escenario activo |
| `snapshot_fn` | `() → None` | Captura snapshot pre-guardado (rules_panel) |
| `prev_derived_fn` | `() → dict \| None` | Lee el snapshot (new_projects, totals) |

---

## 7. API REST

**Archivos:** `backend/api/routes.py`, `backend/api/schemas.py`

Montado en `/api` en `app.py`. Son funciones Starlette puras (no FastAPI), sin decoradores de ruta especiales.

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/status` | Health check `{"status":"ok"}` |
| `GET` | `/api/scenarios` | Lista todos los escenarios |
| `POST` | `/api/scenarios` | Crea nuevo escenario |
| `GET` | `/api/scenarios/{id}` | Obtiene escenario completo |
| `PUT` | `/api/scenarios/{id}` | Actualiza escenario |
| `DELETE` | `/api/scenarios/{id}` | Elimina con cascade |
| `POST` | `/api/scenarios/{id}/varieties` | Agrega variedad con parámetros |
| `PUT` | `/api/varieties/{id}/params` | Actualiza 7 filas de params (bulk) |
| `DELETE` | `/api/varieties/{id}` | Elimina variedad (falla si tiene ha) |
| `GET` | `/api/scenarios/{id}/rules` | Obtiene reglas actuales |
| `PUT` | `/api/scenarios/{id}/rules` | Guarda nuevas reglas |
| `PUT` | `/api/scenarios/{id}/new-projects` | Upsert de celdas de ha |
| `POST` | `/api/scenarios/{id}/recompute` | Retorna DerivedState completo como JSON |
| `GET` | `/api/scenarios/{id}/export.xlsx` | Descarga XLSX con 5 hojas |

Todos los endpoints usan la misma session factory inyectada en el lifespan. El `ScenarioRepo` invalida el caché de Shiny cuando corresponde (a través de `_cache_invalidate`), garantizando que ediciones vía API sean visibles en la UI Shiny sin inconsistencias.

---

## 8. Frontend Astro

**Directorio:** `frontend/`

El frontend es un shell estático mínimo. No tiene lógica de negocio. Su única responsabilidad es mostrar el header corporativo y embeber el dashboard Shiny en un iframe.

```astro
<!-- frontend/src/pages/index.astro -->
<iframe
  src="./shiny/"
  style="width:100%; height: calc(100vh - 64px); border: none;"
/>
```

El proxy de Vite en desarrollo redirige `/shiny/` y `/api/` a `localhost:8000`, de modo que el desarrollador puede usar el HMR de Astro sin cambiar URLs.

### Build para producción

```
pnpm run build
    → frontend/dist/index.html  (con <script type="module" src="/_astro/index.js">)

scripts/inline_js.py
    → lee frontend/dist/_astro/*.js
    → reemplaza el <script src> por <script> con el JS inline
    → corrige la ruta del favicon

Copy-Item frontend/dist/* backend/static/
    → app.py sirve backend/static/ como StaticFiles
```

**Crítico:** el build debe ejecutarse antes de cada deploy. Sin el inlining, el app en ShinyApps.io falla con 404 en los assets `/_astro/*.js` porque ShinyApps.io sirve bajo un sub-path.

---

## 9. Patrones críticos de rendimiento

### 9.1 Caché en memoria (ScenarioState)

**Problema resuelto:** Cada `trigger_reload()` causaba 6-10 queries a Supabase, generando ~700 ms de latencia visible en la UI.

**Solución:** `_state_cache: dict[int, ScenarioState]` en memoria. Las escrituras actualizan el caché in-place con `model_copy(update={...})`. Solo las operaciones sobre variedades (que requieren reconstruir la lista completa) invalidan el caché y fuerzan una re-lectura.

**Tradeoff:** Si múltiples instancias del proceso corren en paralelo (escalado horizontal), el caché puede divergir. Para la escala actual (ShinyApps.io, proceso único), esto no es un problema.

### 9.2 Batch upsert de ha

**Problema resuelto:** `_debounced_flush` enviaba 36 celdas individualmente → 288 queries a Supabase por debounce.

**Solución:** `batch_upsert_ha_cells()` carga todos los mapas de referencia en 5 queries batch al inicio, luego hace todos los upserts en la misma sesión. Total: ~6 queries independientemente del número de celdas.

**Adicionalmente:** `_debounced_flush` compara cada celda contra `_last_saved` y solo envía las que realmente cambiaron. Si el usuario modifica 1 celda, se persiste 1 celda.

### 9.3 selectinload vs. lazy loading

`ScenarioRepo.get()` usa `selectinload` en 6 relaciones. Sin esto, SQLAlchemy emite una query por relación cuando se accede a cada atributo (lazy loading), resultando en 14+ queries secuenciales.

Con `selectinload`, SQLAlchemy emite 6 queries batch (una por relación) que se pueden ejecutar en paralelo en el driver psycopg3.

---

## 10. Variables de entorno

Gestionadas por `backend/settings.py` (Pydantic Settings, carga `.env`).

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./var/app.db` | URL de conexión. Para Supabase: `postgresql+psycopg://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:6543/postgres` |
| `DEBOUNCE_MS` | `1500` | Milisegundos de debounce en la UI Shiny (informativo, el valor real está hardcodeado en `new_projects.py`) |
| `LOG_LEVEL` | `INFO` | Nivel de logs de uvicorn y aplicación |
| `rsconnect_usuario` | — | Usuario de ShinyApps.io |
| `rsconnect_name` | — | Nombre del servidor rsconnect |
| `rsconnect_token` | — | Token de API ShinyApps.io |
| `rsconnect_secret` | — | Secret de API ShinyApps.io |

**Regla:** nunca commitear `.env`. El archivo `.env.example` documenta todas las variables con valores por defecto seguros.

---

## 11. Tests

### Estructura

```
tests/
  conftest.py              ← fixtures globales: engine SQLite memoria, seed, scenario_ui_png
  unit/                    ← una función → un archivo de test
  golden/                  ← vs. docs/image/imagen{7..10}.csv, tolerancia abs≤1
  integration/             ← TestClient Starlette + DB en memoria
  property/                ← Hypothesis: 4 invariantes, max_examples=200
  simulation/              ← test_user_flow_ui_png.py (reproduce UI.png completo)
  e2e/                     ← conftest levanta servidor real en puerto efímero
```

### Comandos útiles

```powershell
# Correr solo los tests que fallan
uv run python -m pytest --lf -v

# Correr un test específico
uv run python -m pytest -k "test_hf_fruta_t2728" -v

# Ver cobertura
uv run python -m pytest tests/unit --cov=backend/logic --cov-report=term-missing

# Hypothesis con más ejemplos
uv run python -m pytest tests/property -v --hypothesis-seed=0
```

### Tolerancia en golden tests

Los valores del UI tienen redondeo implícito. La tolerancia es `abs(actual - expected) ≤ 1` para enteros. Para floats internos: `pytest.approx(expected, rel=1e-3, abs=1e-6)`.

---

## 12. Guía de diagnóstico

### La UI de Shiny no carga (spinner eterno)

1. Verificar que el WebSocket se establece: en DevTools → Network → WS, debe aparecer `/shiny/websocket/`.
2. Si el WebSocket aparece pero inmediatamente cierra: revisar los logs del servidor. Los `CancelledError` en `shiny/reactive/_core.py` son benignos (reconexión del browser). Un `Exception` real tiene un traceback completo.
3. Si no hay WebSocket: verificar que el mount `/shiny` está antes de `StaticFiles` en `app.py`.

### Los valores no se recalculan al cambiar hectáreas

1. Verificar que `_collect_ha` está disparando: agregar `print` temporal en el efecto.
2. Verificar que `batch_upsert_ha_cells` no lanza excepción (está silenciada con `except: pass`).
3. Verificar que `reload_fn()` se llama después del upsert.

### Los deltas KPI no aparecen tras guardar reglas

1. Verificar que `snapshot_fn()` se llama ANTES de `save_rules()` en `rules_panel._on_save()`.
2. Verificar que `prev_derived_fn()` no retorna `None`: el snapshot solo existe si se guardaron reglas al menos una vez.
3. Verificar que la diferencia supera el umbral `abs(delta) >= 0.5`.

### Error `DuplicatePreparedStatement` con Supabase

Este error ocurre cuando Supabase reusa una conexión del pool que tiene un prepared statement residual. Solucionado en `session.py`:

```python
@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, _):
    dbapi_conn.prepare_threshold = 0   # deshabilita caché de prepared statements
    with dbapi_conn.cursor() as cur:
        cur.execute("DEALLOCATE ALL", prepare=False)
```

Si vuelve a aparecer, verificar que la URL contiene `pooler.supabase.com` (activa este código). Si se usa la URL directa (port 5432), no se necesita este fix.

### Error `UnicodeEncodeError` en psycopg3 / Python 3.13

psycopg3 3.3.x realiza DNS lookup síncrono dentro del event loop de asyncio. En entornos donde el hostname contiene caracteres no-ASCII o donde asyncio no permite I/O bloqueante, esto falla. Solucionado en `_supabase_connect_args()`:

```python
import socket
host = parsed.hostname
addr = socket.getaddrinfo(host, None)[0][4][0]   # resuelve a IP antes de crear el engine
return {"hostaddr": addr, "host": host, ...}
```

### La app da 404 al recargar en ShinyApps.io

Causa: `index.html` contiene `<script src="/_astro/index.js">` que no existe bajo el sub-path de ShinyApps.io. Solución: ejecutar `scripts/build.ps1` (que incluye `inline_js.py`) antes del deploy. Verificar en `backend/static/index.html` que no hay referencias a `/_astro/`.

### `AppLocker` bloquea el ejecutable en `.venv\Scripts\`

En el entorno corporativo de Hortifrut, las políticas de AppLocker bloquean ejecutables descargados. Usar siempre:
```powershell
uv run python -m pytest   # no: .venv\Scripts\pytest.exe
uv run python -m uvicorn  # no: .venv\Scripts\uvicorn.exe
```

---

## 13. Problemas conocidos y soluciones aplicadas

| Problema | Causa raíz | Solución aplicada | Archivo |
|---|---|---|---|
| UI congela ~700 ms tras guardar reglas | `load_scenario()` hace 6-10 queries a Supabase en cada reload | Caché en memoria `_state_cache` por `scenario_id` | `shiny_app/state.py` |
| 288 queries por debounce de ha | `upsert_ha_cell` por cada una de las 36 celdas | `batch_upsert_ha_cells` + diff vs. `_last_saved` | `shiny_app/state.py`, `modules/new_projects.py` |
| Server restart por archivos en `scratch/` | uvicorn watchfiles sin exclusiones | `--reload-exclude scratch docs tests frontend` | `scripts/dev.ps1`, `ejecucion.md` |
| `DuplicatePreparedStatement` en Supabase | Transaction pooler no mantiene estado de prepared statements | `prepare_threshold=0` + `DEALLOCATE ALL` en evento connect | `backend/db/session.py` |
| `UnicodeEncodeError` en psycopg3 3.3.x | DNS lookup síncrono en asyncio event loop (Python 3.13) | Pre-resolución de `hostaddr` en `_supabase_connect_args()` | `backend/db/session.py` |
| 404 al recargar en ShinyApps.io | Rutas absolutas `/_astro/*.js` bajo sub-path dinámico | `inline_js.py` inyecta JS directamente en `index.html` | `scripts/inline_js.py` |
| N+1 queries en `ScenarioRepo.get()` | Lazy loading de 6 relaciones ORM | `selectinload` eager en 6 relaciones | `backend/db/repos.py` |
| Variety ops en 14 queries | Loop individual DELETE + INSERT por fila | `sql_delete` bulk + `bulk_insert_mappings` | `shiny_app/state.py` |
| `asyncio.CancelledError` en logs de desarrollo | WebSocket cerrado mientras Shiny tiene tarea reactiva pendiente (reconexión browser) | Comportamiento benigno; no requiere acción | N/A |
