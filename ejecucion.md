# Guía de Ejecución — HF Breeding Planner

> **Proyecto:** HF Breeding Planner — Business Planning 2026 (Hortifrut Perú)
> **Stack:** Starlette + Shiny for Python + Astro · SQLite dev / Supabase Postgres cloud

---

## 1. Requisitos Previos

### 1.1 Software

| Software | Versión mínima | Verificar con |
|----------|---------------|---------------|
| Python | 3.11+ | `python --version` |
| uv | latest | `uv --version` |
| Node.js | 18+ | `node --version` |
| pnpm | latest | `pnpm --version` |
| Git | 2.30+ | `git --version` |

Instalar `uv` (si no está):

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Habilitar `pnpm` via corepack (Node incluye corepack desde v16.13):

```powershell
corepack enable
corepack prepare pnpm@latest --activate
```

### 1.2 Cuentas (solo para despliegue)

- **ShinyApps.io**: cuenta activa con token/secret generados en el dashboard.

---

## 2. Instalación Local

### 2.1 Clonar y preparar entorno Python

```powershell
git clone <url-del-repo>
cd hf-analytics_calculadora_analitycs

# Instalar todas las dependencias (runtime + dev) desde uv.lock
uv sync
```

> **Nota AppLocker (entorno corporativo):** si la política bloquea ejecutables en `.venv\Scripts\`,
> usar siempre `uv run python -m <herramienta>` en lugar del binario directo.

### 2.2 Instalar dependencias del frontend

```powershell
cd frontend
pnpm install
cd ..
```

### 2.3 Configurar variables de entorno

```powershell
Copy-Item .env.example .env
# Editar .env con los valores reales si se cambia el motor de DB
```

Variables clave en `.env`:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./var/app.db` | URL de la base de datos |
| `DEBOUNCE_MS` | `1500` | Milisegundos de debounce en la UI |
| `LOG_LEVEL` | `INFO` | Nivel de logs del servidor |

### 2.4 Sembrar la base de datos (primera vez)

```powershell
uv run python scripts/seed_dev_db.py
```

Esto crea `var/app.db` con el escenario canónico de UI.png ya cargado.

---

## 3. Ejecución en Desarrollo

### 3.1 Opción A — Script automático (recomendado)

```powershell
# Abre dos ventanas PowerShell: backend en :8000 y Astro dev en :4321
.\scripts\dev.ps1
```

### 3.2 Opción B — Manual (2 terminales)

**Terminal 1 — Backend (Starlette + Shiny):**

```powershell
uv run python -m uvicorn app:app --reload --port 8000 --reload-exclude ".venv" --reload-exclude "scratch" --reload-exclude "docs" --reload-exclude "tests" --reload-exclude "frontend"
```

**Terminal 2 — Frontend (Astro dev server):**

```powershell
cd frontend
pnpm run dev
```

### 3.3 URLs de acceso

| Servicio | URL |
|----------|-----|
| Shell Astro (dev) | http://localhost:4321 |
| App completa (backend estático) | http://localhost:8000 |
| Dashboard Shiny | http://localhost:8000/shiny/ |
| API status | http://localhost:8000/api/status |

### 3.4 Checklist de verificación rápida

- [ ] `localhost:8000/api/status` retorna `{"status": "ok"}`
- [ ] `localhost:8000/shiny/` carga la app Shiny con las 5 secciones
- [ ] `localhost:8000/` carga el shell Astro con el título "Business Planning 2026"
- [ ] La Sección 5 (Totales) muestra `5,525` en HF Fruta T2728

---

## 4. Build para Producción

### 4.1 Compilar todo (script completo)

```powershell
.\scripts\build.ps1
```

El script ejecuta en secuencia:
1. `pnpm run build` dentro de `frontend/`
2. `uv run python scripts/inline_js.py` — inyecta JS inline y corrige rutas de favicon
3. Copia `frontend/dist/*` → `backend/static/`

### 4.2 Pasos manuales equivalentes

```powershell
cd frontend
pnpm run build
cd ..

uv run python scripts/inline_js.py

New-Item -ItemType Directory -Path backend\static -Force
Copy-Item -Path frontend\dist\* -Destination backend\static\ -Recurse -Force
```

### 4.3 Verificar build localmente

```powershell
uv run python -m uvicorn app:app --port 8000
```

Abrir http://localhost:8000 — debe mostrar el shell Astro con el iframe de Shiny embebido.

> **Por qué `inline_js.py`:** ShinyApps.io sirve la app bajo un sub-path dinámico
> (`/<usuario>/<nombre-app>/`). Las rutas absolutas `/_astro/*.js` generadas por Astro
> se rompen en ese entorno. El script inyecta el JS directamente en `index.html` para
> eliminar cualquier referencia absoluta a `/_astro/`.

---

## 5. Despliegue en ShinyApps.io

> [!IMPORTANT]
> **Siempre** ejecutar `.\scripts\build.ps1` antes de desplegar. Si se salta este paso
> se subirá una versión desactualizada del frontend.

### 5.1 Pre-vuelo

```powershell
# 1. Recompilar frontend (CSS/JS inline)
.\scripts\build.ps1

# 2. Verificar que .rscignore excluye frontend/, tests/, docs/, scripts/, .venv/
Get-Content .rscignore

# 3. Verificar requirements.txt actualizado
# (generado con: uv pip compile pyproject.toml -o requirements.txt)
Get-Content requirements.txt | Select-Object -First 5
```

### 5.2 Configurar cuenta rsconnect

```powershell
# Cargar variables del .env
Get-Content .env | ForEach-Object {
    if ($_ -match "^(?<name>[^#\s=]+)=(?<value>.*)$") {
        $env:($Matches.name) = $Matches.value.Trim('"')
    }
}

# Registrar cuenta
uv run python -c "from rsconnect.main import cli; cli()" add --account $env:rsconnect_usuario --name $env:rsconnect_name --token $env:rsconnect_token --secret $env:rsconnect_secret
```

### 5.3 Primer despliegue

```powershell
uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name $env:rsconnect_usuario --title "calculadora_analitycs" --new
```

> **Nota:** el entrypoint es `app:app` (Starlette), no FastAPI — ShinyApps.io no soporta
> `python-fastapi`. Los endpoints API están implementados como funciones Starlette puras.

### 5.4 Redeploys (actualizaciones)

Una vez desplegada, anotar el `app-id` que aparece en el dashboard de ShinyApps.io:

```powershell
# APP_ID: 17366145
uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name alex-prieto --app-id 17366145
```

> El `app-id` aparece en la URL del dashboard de ShinyApps.io y también en la salida
> del primer deploy. Registrarlo aquí para no tener que buscarlo en cada redeploy.

### 5.5 Verificación post-despliegue

- [ ] URL pública accesible
- [ ] Iframe de Shiny carga
- [ ] CRUD de escenarios funciona contra Supabase
- [ ] Sub-totales reproducen los valores de UI.png
- [ ] Recarga de página **NO** da 404 (patrón SPA, rutas relativas)
- [ ] Export XLSX descargable

---

## 6. Troubleshooting

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| 404 al recargar en ShinyApps.io | Rutas absolutas en el build | Verificar que `inline_js.py` corrió; revisar `index.html` sin `/_astro/` |
| Fetch a la API falla en producción | URL absoluta `/api/` en vez de `./api/` | Auditar `frontend/src/` con `grep -r '"/api'` |
| Shiny no conecta (WebSocket) | Middleware de sanitización bloqueando WS | Verificar que el mount `/shiny` está antes del `StaticFiles` en `app.py` |
| `numpy` no instala en Python 3.13 | Wheels no disponibles para `numpy < 2.1` | Fijar `numpy>=2.1.0` en `pyproject.toml` |
| Conexiones colgadas en Supabase | Pool doble (SQLAlchemy + Supavisor) | Verificar que `session.py` usa `NullPool` cuando la URL contiene `pooler.supabase.com` |
| `playwright` no encuentra Chromium | Binario no instalado | `uv run python -m playwright install chromium` |
| Herramienta de `.venv\Scripts\` bloqueada | AppLocker corporativo | Usar `uv run python -m <herramienta>` en lugar del ejecutable directo |
| El servidor no arranca en 30 s (tests E2E) | Puerto ocupado o DB corrupta | Verificar que ningún uvicorn corre en el puerto; borrar la DB efímera si existe |

---

## 7. Tests

### 7.1 Tests unitarios

```powershell
uv run python -m pytest tests/unit -v
```

Cubre toda la lógica de cálculo puro (`backend/logic/`): variedades, lag matrix, bloques B1/B2/B3, plantines, terceros, totales.

### 7.2 Tests golden (datos reales)

```powershell
uv run python -m pytest tests/golden -v
```

Compara los outputs del motor contra los CSVs de `docs/image/imagen{7..10}.csv`. Tolerancia `abs ≤ 1` para enteros del UI.

### 7.3 Tests de integración (API + DB)

```powershell
uv run python -m pytest tests/integration -v
```

Levanta un servidor Starlette con SQLite en memoria. Cubre todos los endpoints REST y el round-trip de `ScenarioState`.

### 7.4 Tests de propiedades (Hypothesis)

```powershell
uv run python -m pytest tests/property -v
```

Verifica invariantes del motor: no-negatividad, idempotencia, monotonía y linealidad. `max_examples=200`.

### 7.5 Tests E2E (Playwright)

```powershell
uv run python -m pytest tests/e2e -v
```

Levanta internamente un uvicorn real con SQLite efímera sembrada. Abre Chromium headless y verifica el flujo completo de UI.png (7 tests, ~14 s).

### 7.6 Suite completa

```powershell
uv run python -m pytest -v
```

Ejecuta todas las suites en orden. El servidor E2E se comparte a nivel de sesión para minimizar tiempo de arranque.
