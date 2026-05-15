# Arquitectura — HF Breeding Planner

> **Audiencia:** Arquitectos de solución, líderes técnicos y gerentes de TI.
> **Alcance:** Describe la estructura del sistema, las interacciones entre componentes y el modelo de despliegue. Para la especificación funcional y fórmulas de negocio, ver [`docs/description_proyecto.md`](../description_proyecto.md).

---

## 1. Visión General del Sistema (C4 – Nivel Contexto)

El sistema es una aplicación web monolítica de un solo proceso Python. Todos los componentes (API, dashboard reactivo y archivos estáticos) se sirven desde el mismo proceso ASGI, lo que lo hace desplegable en ShinyApps.io sin infraestructura adicional.

```mermaid
flowchart TB
    subgraph Actores["Actores"]
        U1["👤 Analista de Producción\nHortifrut Perú"]
        U2["👤 Gerente de Negocio"]
    end

    subgraph Sistema["HF Breeding Planner · ShinyApps.io"]
        direction TB
        APP["Aplicación Web\nStarlette + Shiny + Astro\n─────────────────\nPython 3.13 · ASGI"]
    end

    subgraph Datos["Persistencia"]
        DB[("Supabase PostgreSQL\n─────────────\nTransaction Pooler\naws-0-us-east-1")]
    end

    U1 -->|"Modela escenarios,\nedita hectáreas y reglas"| APP
    U2 -->|"Consulta totales\ny exporta XLSX"| APP
    APP <-->|"Lee / escribe\nestado del escenario\nSQLAlchemy + NullPool"| DB
```

**Decisiones arquitectónicas clave:**
- **Un solo proceso** elimina latencia de red interna entre API y motor de cálculo.
- **Starlette** (no FastAPI) es el único framework ASGI compatible con ShinyApps.io.
- **Supabase** proporciona Postgres gestionado con pooler de transacciones, eliminando infraestructura propia.

---

## 2. Componentes Internos (C4 – Nivel Contenedor)

```mermaid
flowchart LR
    subgraph Browser["Navegador del Usuario"]
        ASTRO["Astro SPA\n──────────\nShell HTML/CSS/JS\nestático e inline"]
        IFRAME["iframe src='./shiny/'\n──────────\nEmbebe el dashboard\nShiny completo"]
    end

    subgraph Proceso["Proceso Python · Puerto 8000"]
        direction TB
        ROUTER["Starlette Router\n──────────\nMux de rutas entrantes"]
        SHINY["Shiny App\n/shiny/*\n──────────\nWebSocket reactivo\n5 módulos UI"]
        API["REST API\n/api/*\n──────────\nCRUD escenarios\nexport XLSX"]
        STATIC["StaticFiles\n/ (último)\n──────────\nSirve Astro build\ncon fallback HTML"]

        subgraph Motor["Motor de Cálculo (puro)"]
            RECOMPUTE["recompute.py\n──────────\nPipeline topológico\nPandas · NumPy"]
        end

        subgraph Persistencia["Capa de Persistencia"]
            CACHE["Caché en Memoria\n_state_cache\n──────────\nScenarioState por\nscenario_id"]
            REPOS["Repositorios\n──────────\nScenarioRepo\nRulesRepo\nAuditRepo"]
        end
    end

    subgraph Cloud["Supabase Cloud"]
        DB[("PostgreSQL\n──────────\nNullPool\nprepare_threshold=0")]
    end

    ASTRO --> IFRAME
    ASTRO -->|"fetch /api/*\n(CRUD, export)"| API
    IFRAME <-->|"WebSocket\npersistente"| SHINY
    ROUTER --> SHINY
    ROUTER --> API
    ROUTER --> STATIC
    SHINY --> RECOMPUTE
    SHINY --> CACHE
    API --> REPOS
    CACHE -->|"miss → lee"| REPOS
    REPOS <-->|"SQLAlchemy 2.x\nselectinload eager"| DB
    CACHE -->|"escribe en-place\nmodel_copy(update={})"| CACHE
```

**Flujo de una petición típica (editar hectáreas):**
1. El usuario modifica un valor en la grilla → WebSocket Shiny recibe el evento.
2. Debounce de 1.5 s acumula cambios; solo envía las celdas que difieren del estado guardado.
3. `batch_upsert_ha_cells()` abre una sesión SQLAlchemy, carga mapas en 5 queries batch, hace los upserts y cierra.
4. La caché en memoria se actualiza en-place; `trigger_reload()` incrementa el contador reactivo.
5. `recompute()` recorre el pipeline topológico y produce el nuevo `DerivedState`.
6. Los módulos UI re-renderizan con los nuevos valores.

---

## 3. Pipeline de Cálculo (DAG Topológico)

El motor de cálculo es completamente puro: no lee ni escribe base de datos, no tiene efectos secundarios. Recibe un `ScenarioState` inmutable y devuelve un `DerivedState` serializable.

```mermaid
flowchart TB
    STATE(["ScenarioState\n─────────────────\nPydantic · frozen=True\nVariedades · Reglas\nHectáreas · Tabla Base"])

    CALC["calculos_variedades\n─────────────────\nProductividad · Densidad · Precio\npor Variedad × Año de Planta\n3 tipos: HFI · HFT · Terceros"]

    subgraph Paralelo["Bloques Independientes (paralelizables)"]
        direction LR
        B1["crecimiento_hf\n─────\nBloque B1\nCHAO · OLMOS\nha × Productividad\n÷ 1 000"]
        B2["recambio\n─────\nBloque B2\nVariedades\nexistentes\nen recambio"]
        B3["nuevos_terceros\n─────\nBloque B3\nTalsa · Diamond Bridge\nProducción HFT\n+ Ganancia ROY"]
    end

    PLANT["plantines\n─────────────────\nha × Densidad × Costo\n÷ Financiamiento (años)\nTruncado: n > fin_años → 0"]

    TER["terceros_totales\n─────────────────\nSolo ha B3\nProducción y Ganancia\npara productores externos"]

    TOT["totales\n─────────────────\nHortifrut: B1+B2+B3+plantines\nTerceros: terceros_totales\npor temporada T2627→T3132"]

    OUT(["DerivedState\n─────────────────\ndict serializable\nPor variedad · bloque · temporada\nTotal HF · Total Terceros"])

    STATE --> CALC
    CALC --> B1
    CALC --> B2
    CALC --> B3
    B3 --> PLANT
    B3 --> TER
    B1 --> TOT
    B2 --> TOT
    PLANT --> TOT
    TER --> TOT
    TOT --> OUT
```

**Unidades de salida:** toneladas (tn) para producción y miles de USD para ganancias. La conversión ocurre al final de cada bloque (`÷ 1 000`), no durante el cálculo intermedio.

---

## 4. Flujo Reactivo — Guardar Reglas con KPI Delta

Este diagrama describe la interacción más compleja del sistema: el guardado de reglas en Sección 3 con retroalimentación visual de impacto en Secciones 4 y 5.

```mermaid
sequenceDiagram
    actor U as Usuario
    participant R as Sección 3 · rules_panel
    participant A as app.py · server()
    participant S as state.py · caché
    participant DB as Supabase PostgreSQL
    participant N as Sección 4 · new_projects
    participant T as Sección 5 · totals

    U->>R: Edita "Royaltie FOB" → clic "Guardar Reglas"

    rect rgb(240, 248, 255)
        note over A: Fase 1 — Snapshot pre-guardado
        R->>A: snapshot_fn()
        A->>A: _snapshot_derived = current_derived()
        note over A: Captura derived VIEJO antes del cambio
    end

    rect rgb(240, 255, 240)
        note over S,DB: Fase 2 — Persistencia
        R->>S: save_rules(scenario_id, rules)
        S->>DB: UPDATE rules SET royaltie_fob=... (1 query)
        DB-->>S: OK
        S->>S: _state_cache[id].rules = new_rules
        note over S: Cache actualizado in-place sin re-leer DB
    end

    rect rgb(255, 250, 240)
        note over A: Fase 3 — Recálculo reactivo
        R->>A: reload_fn()
        A->>A: _reload_counter += 1
        A->>S: load_scenario() → cache hit instantáneo
        S-->>A: ScenarioState (nuevas reglas)
        A->>A: recompute(state) → DerivedState NUEVO
    end

    rect rgb(255, 245, 255)
        note over N,T: Fase 4 — Re-render con deltas
        A->>N: new_projects_content(derived=NUEVO, prev=SNAPSHOT)
        A->>T: totals_table(derived=NUEVO, prev=SNAPSHOT)
        N-->>U: Sub-totales + badges ▲ verde / ▼ rojo
        T-->>U: Totales + badges ▲ verde / ▼ rojo
    end
```

**Latencia esperada:** < 300 ms total (DB write ~100 ms, recompute ~50 ms, re-render ~50 ms).

---

## 5. Modelo de Datos (Esquema Relacional)

```mermaid
flowchart TB
    subgraph Core["Entidad Principal"]
        SCN["scenario\n─────────\nid · name · country\nstart_season · end_season\nlocked · created_at"]
    end

    subgraph Temporadas["Temporadas"]
        SEA["season\n─────────\nid · scenario_id\ncode: T2627..T3132\nposition"]
    end

    subgraph Tabla["Tabla Base"]
        BTR["base_table_row\n─────────\nid · scenario_id\nproject_name · unit · total"]
        BTV["base_table_value\n─────────\nrow_id · season_id · value"]
        BTVAR["base_table_variation\n─────────\nscenario_id · season_id\nvalue"]
    end

    subgraph Variedades["Variedades Agronómicas"]
        VAR["variety\n─────────\nid · scenario_id\nname · position"]
        VP["variety_param\n─────────\nvariety_id · plant_year 1-7\nproductividad · densidad\nprecio_estimado · pct_recaudacion"]
    end

    subgraph Reglas["Reglas del Escenario"]
        RUL["rules\n─────────\nscenario_id (1:1)\nroyaltie_fob · costo_plantines\ninteres_financiamiento\nfinanciamiento_anios"]
    end

    subgraph Proyectos["Nuevos Proyectos (sparse)"]
        NPG["new_project_group\n─────────\nid · scenario_id\nkind: B1 / B2 / B3"]
        NPS["new_project_subrow\n─────────\ngroup_id · variety_id · label"]
        NPH["new_project_ha\n─────────\nsubrow_id · season_id\nhectareas"]
    end

    subgraph Audit["Auditoría"]
        AUD["audit_log\n─────────\nid · entity · payload JSON\ncreated_at"]
    end

    SCN -->|"1:N cascade"| SEA
    SCN -->|"1:N cascade"| BTR
    BTR -->|"1:N"| BTV
    SCN -->|"1:N"| BTVAR
    SCN -->|"1:N cascade"| VAR
    VAR -->|"1:7 UNIQUE(variety_id, plant_year)"| VP
    SCN -->|"1:1"| RUL
    SCN -->|"1:N"| NPG
    NPG -->|"1:N"| NPS
    NPS -->|"1:N sparse"| NPH
    SEA -.->|"FK season_id"| BTV
    SEA -.->|"FK season_id"| BTVAR
    SEA -.->|"FK season_id"| NPH
    VAR -.->|"FK variety_id"| NPS
```

**Nota sobre datos derivados:** Las matrices de producción, ganancia y subtotales **no se persisten**. Se calculan en memoria con Pandas/NumPy en cada recarga del escenario, garantizando consistencia sin riesgo de datos cacheados obsoletos en DB.

---

## 6. Arquitectura de Despliegue

```mermaid
flowchart LR
    subgraph Dev["Entorno de Desarrollo (local)"]
        direction TB
        DEV_CMD[".\scripts\dev.ps1"]
        DEV_BE["uvicorn :8000\nStarlette + Shiny\n--reload (watchfiles)"]
        DEV_FE["Astro dev :4321\nHMR + proxy → :8000"]
        DEV_DB[("SQLite\nvar/app.db\ncreate_all automático")]
        DEV_CMD --> DEV_BE
        DEV_CMD --> DEV_FE
        DEV_BE --- DEV_DB
    end

    subgraph Build["Pipeline de Build"]
        direction TB
        B1["pnpm run build\nAstro → frontend/dist/"]
        B2["scripts/inline_js.py\nInyecta /_astro/*.js\nen index.html"]
        B3["Copy-Item\nfrontend/dist/ →\nbackend/static/"]
        B1 --> B2 --> B3
    end

    subgraph Prod["Producción — ShinyApps.io"]
        direction TB
        RSCN["rsconnect deploy\n--entrypoint app:app\n--new / --app-id"]
        BUNDLE["Bundle (.tar.gz)\napp.py + backend/\nrequirements.txt\n(sin frontend/, tests/, docs/)"]
        PROD_APP["app:app\nStarlette ASGI\npuerto dinámico ShinyApps"]
        PROD_STATIC["backend/static/\nAstro index.html\nJS inline, sin /_astro/"]
        PROD_DB[("Supabase\nPostgreSQL\nNullPool · pooler :6543")]
        RSCN --> BUNDLE --> PROD_APP
        PROD_APP --- PROD_STATIC
        PROD_APP <--> PROD_DB
    end

    Build -->|"genera"| PROD_STATIC
    Build --> RSCN

    style Dev fill:#f0f9ff,stroke:#3b82f6
    style Build fill:#f0fdf4,stroke:#16a34a
    style Prod fill:#fefce8,stroke:#ca8a04
```

**Por qué `inline_js.py`:** ShinyApps.io sirve la app bajo un sub-path dinámico (e.g. `/usuario/app-name/`). Las rutas absolutas `/_astro/*.js` generadas por Astro rompen en ese contexto. El script inyecta el JS directamente en `index.html`, eliminando todas las referencias a `/_astro/`.

---

## 7. Decisiones Arquitectónicas Relevantes

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Starlette como host ASGI | FastAPI | ShinyApps.io no soporta `python-fastapi`; los endpoints son funciones puras sin decoradores FastAPI |
| `NullPool` para Supabase | Pool por defecto | Supavisor (transaction pooler) ya gestiona el pool; doble pool causa errores de conexión colgada |
| `prepare_threshold=0` en psycopg3 | Sin configuración | El transaction pooler no mantiene estado de prepared statements entre conexiones; causa `DuplicatePreparedStatement` |
| Caché en memoria por `scenario_id` | Re-lectura a DB en cada reload | Elimina 6-10 queries a Supabase en cada cambio de UI, reduciendo latencia de ~700 ms a ~200 ms |
| `selectinload` eager en `ScenarioRepo.get()` | Lazy loading por defecto | Evita el problema N+1: 1 escenario con 6 relaciones = 6 queries batch vs. 14+ queries lazy |
| Cálculo puro en memoria (sin persistir derived) | Guardar derived en DB | Garantiza consistencia sin riesgo de cache stale; Pandas opera sobre arrays en microsegundos |
| Snapshot del derived antes de guardar reglas | Comparar al re-render | Permite mostrar el delta exacto sin re-calcular con reglas antiguas; el snapshot se captura síncronamente antes del `save_rules` |
| `hostaddr` pre-resuelto en `session.py` | Resolución DNS normal | psycopg3 3.3.x hace DNS lookup síncrono dentro del event loop de asyncio en Python 3.13, causando `UnicodeEncodeError` |
