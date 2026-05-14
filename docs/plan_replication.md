# Plan de Replicación: Arquitectura "Agro-Stack" (Astro + Starlette/API + Shiny)

Este documento detalla los pasos y las mejores prácticas para replicar la arquitectura híbrida implementada en el repositorio. Esta pila ("stack") combina la velocidad y SEO de **Astro** (Frontend), la ligereza de **Starlette** (Backend/Gateway), y la interactividad analítica de **Shiny for Python**.

El objetivo es permitir que cualquier nuevo proyecto pueda adoptar esta arquitectura y desplegarse exitosamente en plataformas de RStudio/Posit como **ShinyApps.io** o **Posit Connect**, sin sufrir problemas de enrutamiento.

---

## 🏗️ 1. Entendiendo la Arquitectura

1. **Frontend (Astro)**: Construye la interfaz de usuario. Al compilarse, genera archivos estáticos (HTML, CSS).
2. **Interactividad Analítica (Shiny for Python)**: Se encarga de la visualización de datos pesada (mapas, gráficos complejos) incrustada vía iframe.
3. **Backend y API Gateway (Starlette)**: Actúa como el punto de entrada principal (`app.py`). Sirve los archivos estáticos de Astro en la ruta raíz (`/`), expone endpoints de datos rápidos (KPIs) en `/api`, y monta la aplicación de Shiny en `/shiny/`. *Nota: Se usa Starlette puro en lugar de FastAPI porque ShinyApps.io tiene una compatibilidad nativa más estable con ASGI estándar en sus configuraciones.*

---

## 📁 2. Estructura de Carpetas del Proyecto

La siguiente es la estructura de referencia que debe mantener un nuevo proyecto con esta arquitectura. Los archivos y carpetas marcadas con `*` son generados automáticamente y **no deben commitearse** (incluirlos en `.gitignore` y `.rscignore`).

```
proyecto-agro-stack/
│
├── app.py                      # Entrypoint para ShinyApps.io (Starlette)
├── requirements.txt            # Dependencias de Python (producción)
├── .env                        # Variables de entorno locales (NO commitear) *
├── .env.example                # Plantilla de variables de entorno (commitear)
├── .gitignore                  # Exclusiones para Git
├── .rscignore                  # Exclusiones para ShinyApps.io
│
├── backend/                    # Lógica del servidor Python
│   ├── __init__.py
│   ├── main.py                 # Servidor FastAPI para desarrollo local
│   ├── engine.py               # Lógica de negocio: KPIs, Gantt, filtros
│   ├── dashboard.py            # Aplicación Shiny for Python
│   ├── static/                 # HTML compilado de Astro (NO commitear) *
│   └── data/                   # Datos fuente usados en producción
│
├── frontend/                   # Código fuente de Astro
│   ├── src/
│   │   └── pages/
│   │       └── index.astro     # Única página (SPA)
│   ├── public/                 # Activos estáticos (favicon, imágenes)
│   ├── dist/                   # Build generado (NO commitear) *
│   ├── node_modules/           # Dependencias JS (NO commitear) *
│   ├── astro.config.mjs
│   ├── package.json
│   ├── pnpm-lock.yaml          # Lockfile de pnpm (SÍ commitear)
│   ├── pnpm-workspace.yaml     # Config de workspace (SÍ commitear)
│   └── tsconfig.json
│
├── data/                       # Datos fuente del proyecto
│   ├── datos_final.csv         # CSV principal (NO commitear si es grande) *
│   ├── cosecha_manual.json     # Ajustes manuales (commitear si es pequeño)
│   └── config_excepciones.csv  # Excepciones de negocio (commitear)
│
├── notebooks/                  # Exploración y ETL exploratorio
│   ├── etl_polars.py           # Script ETL principal (commitear)
│   └── *.ipynb / *.csv         # Artefactos exploratorios (NO commitear) *
│
├── scripts/                    # Utilidades de desarrollo y despliegue
│   ├── dev.ps1                 # Script PowerShell para dev rápido
│   └── inline_js.py            # Post-procesador de JS para ShinyApps.io
│
├── src/                        # Pipelines de datos
│   ├── 01_pipeline_athena.py
│   └── 02_pipeline_catastro.py
│
├── test/                       # Tests del backend
│   ├── test_api.py
│   └── test_engine.py
│
└── docs/                       # Documentación del proyecto
    ├── ejecucion.md
    └── plan_replication.md
```

---

## ⚠️ 3. Aprendizaje Crítico: El Problema de las Páginas Dinámicas en Astro

Al desplegar en infraestructuras como **ShinyApps.io**, el servidor asigna una URL única que incluye un "slug" de *worker* dinámico (por ejemplo, `/_w_1234abcd/`). 

**El Problema**:
Si utilizamos enrutamiento dinámico en Astro (múltiples páginas físicas o Server-Side Rendering) y el usuario navega a `miprojeto.shinyapps.io/dashboard/`, la plataforma de ShinyApps intentará resolver esa ruta físicamente en el servidor proxy, lo que causará un error (404 Not Found) porque la plataforma espera que la URL base se mantenga o que el enrutamiento lo maneje un único punto de entrada. Además, si el usuario recarga la página, se perderá la sesión del worker.

**La Solución (Regla de Oro)**:
*   **No usar páginas múltiples ni enrutamiento dinámico en Astro.** 
*   Todo el frontend debe construirse como una **Single Page Application (SPA)**, es decir, una única página (ej. `index.astro`).
*   La navegación entre vistas (ej. de "Inicio" a "Dashboard") debe manejarse mediante **estado del lado del cliente** (React, Svelte, o Vanilla JS) o mediante **Hash Routing** (`/#dashboard`), asegurando que la URL física no cambie para el servidor de ShinyApps.
*   Todos los enlaces y referencias a recursos (imágenes, scripts, fetch) deben ser **estrictamente relativos** (ej. `./api/datos`, no `/api/datos`).

---

## 🛠️ 4. Guía Paso a Paso para un Nuevo Proyecto

### Paso 4.1: Configurar el Entorno Python con `uv` (Recomendado)

> [!TIP]
> `uv` es significativamente más rápido que `pip` y resuelve dependencias de forma determinista. Úsalo siempre para proyectos nuevos.

```powershell
# 1. Instalar uv (solo una vez por máquina)
pip install uv

# 2. Crear entorno virtual (más rápido que python -m venv)
uv venv

# 3. Instalar dependencias desde requirements.txt
uv pip install -r requirements.txt

# 4. Ejecutar scripts dentro del entorno sin activarlo explícitamente
uv run python script.py
uv run python -m uvicorn backend.main:app --reload --port 8000 --reload-exclude ".venv"
```

El archivo `requirements.txt` debe incluir al menos:
```
fastapi>=0.115.0
uvicorn>=0.34.0
starlette>=0.45.0
shiny>=1.2.0
pandas>=2.2.0
numpy>=2.1.0     # Requiere >=2.1.0 para Python 3.13 (wheels pre-compiladas)
plotly>=6.0.0
rsconnect-python>=1.28.0
```

> [!IMPORTANT]
> Si usas **Python 3.13**, no pines `numpy==1.26.x` — esa versión no tiene wheels para 3.13 y requiere compilar desde fuente (falla en Windows). Usa `numpy>=2.1.0`.

### Paso 4.2: Configurar el Frontend (Astro) con `pnpm`

> [!TIP]
> Usa `pnpm` en lugar de `npm`. Evita *phantom dependencies* (paquetes accedidos sin estar declarados) y es más rápido gracias a su store compartido.

```powershell
# 1. Habilitar pnpm (viene incluido en Node.js >= 16.9 via corepack)
corepack enable
corepack prepare pnpm@latest --activate

# 2. Verificar instalación
pnpm --version

# 3. Inicializar Astro en la carpeta frontend
pnpm create astro@latest frontend
# Seleccionar: Empty project, TypeScript: Strict, no instalar dependencias aún

# 4. Instalar dependencias (desde la carpeta frontend/)
cd frontend
pnpm install

# Aprobar builds de paquetes binarios (esbuild, sharp) - solo primera vez
pnpm approve-builds
```

**Configurar `astro.config.mjs`** — Forzar SPA y CSS inline:
```javascript
import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',
  build: {
    inlineStylesheets: 'always',  // CSS inline: evita rutas /_astro/ rotas en ShinyApps
  },
  vite: {
    server: {
      proxy: {
        '/api':   { target: 'http://localhost:8000', changeOrigin: true },
        '/shiny': { target: 'http://localhost:8000', changeOrigin: true, ws: true }
      }
    }
  }
});
```

### Paso 4.3: Configurar el Backend y API Gateway (Starlette)

Starlette será el único servicio expuesto en producción. Interceptará la URL y servirá tanto a Astro como a Shiny.

1.  **Crear el archivo principal** (`app.py`):

    ```python
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount
    from starlette.staticfiles import StaticFiles
    from backend.dashboard import app as shiny_dashboard_app # Tu app de Shiny

    # 1. Definir Endpoints de la API
    async def api_status(request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "1.0.0"})

    async def api_dashboard(request) -> JSONResponse:
        # Aquí procesas datos con Pandas y retornas JSON
        return JSONResponse({"kpis": {}, "gantt": []})

    # 2. Configurar Rutas
    api_routes = [
        Route("/api/status", api_status),
        Route("/api/dashboard", api_dashboard),
    ]

    all_routes = list(api_routes)
    
    # 3. Montar Shiny en un subdirectorio
    all_routes.append(Mount("/shiny", app=shiny_dashboard_app))

    # 4. Montar Astro en la raíz (DEBE IR AL FINAL)
    all_routes.append(Mount("/", app=StaticFiles(directory="backend/static", html=True), name="static"))

    app = Starlette(routes=all_routes)
    ```

### Paso 4.4: Integrar Shiny for Python

Crea tu dashboard interactivo en `backend/dashboard.py`. Esta aplicación será consumida desde Astro a través de un `iframe` que apunte a la ruta relativa `./shiny/`.

```html
<!-- En tu index.astro -->
<iframe src="./shiny/" width="100%" height="800px" style="border:none;"></iframe>
```

---

## 🚀 5. Pipeline de Compilación y Despliegue Unificado

Para enviar esto a ShinyApps.io, debes compilar el frontend y empaquetar todo para que el servidor remoto vea a Starlette (`app.py`) como el punto de entrada principal.

```powershell
# 0. Prerequisitos: Dar permisos de ejecución (solo una vez por sesión de terminal)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 1. Compilar Astro con pnpm
cd frontend
pnpm run build
cd ..

# 2. Post-procesar: inyectar JS inline y corregir rutas de favicon
#    (Evita errores de rutas /_astro/ en ShinyApps.io)
uv run python scripts/inline_js.py

# 3. Copiar estáticos compilados al backend
xcopy /E /Y frontend\dist\* backend\static\

# 4. Desplegar con rsconnect usando uv run
#    (Usar 'uv run python -c ...' para acceder al entorno virtual correctamente)
uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name tu_usuario --title "Nombre_App"

# Para re-despliegues en una app existente (usando --app-id)
uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name tu_usuario --app-id TU_APP_ID
```

> [!IMPORTANT]
> El `.rscignore` es crítico. Sin él, rsconnect incluirá `notebooks/`, `docs/`, `frontend/` y otras carpetas pesadas en el bundle. Esto no solo hace el despliegue más lento, sino que puede causar errores de **checksum mismatch** si el servidor intenta verificar archivos que cambiaron entre el manifest y el bundle final.

**Contenido mínimo recomendado de `.rscignore`**:
```
# Frontend (ya compilado en backend/static/)
frontend/
frontend/*
node_modules/
node_modules/*

# Notebooks exploratorios
notebooks/
notebooks/*

# Documentación (no requerida en producción)
docs/
docs/*

# Tests
test/
test/*

# Scripts de desarrollo local
scripts/
scripts/*

# Entorno virtual (ShinyApps instala desde requirements.txt)
.venv/
venv/

# Datos de salida regenerables
data/output/

# Archivos de secretos
.env
```

---

## 💡 6. Optimizaciones Críticas (Rendimiento y UX)

Basado en implementaciones exitosas, todo nuevo proyecto con esta arquitectura debería aplicar:

1.  **Vectorización con Pandas**: Evita iterar sobre DataFrames (`iterrows`, `apply` por filas) para cálculos lógicos de backend. Usa operaciones vectorizadas (ej. `np.where`, `isin`, `.str.contains`) agrupando por llaves principales para asegurar que la API responda en milisegundos incluso con miles de registros.
2.  **Consolidación de APIs**: En lugar de hacer múltiples peticiones separadas desde el frontend (una para KPIs, otra para la tabla principal), consolida todo en un endpoint integral (`/api/dashboard`) que envíe un solo JSON con toda la estructura. Esto reduce la latencia de red.
3.  **Interactividad Bidireccional de Filtros**: 
    *   **En el backend**: El endpoint `/api/filters` debe escuchar el estado actual de *todos* los filtros aplicados y retornar solo las opciones compatibles.
    *   **En el frontend**: Además de usar selectores clásicos (comboboxes), transforma los KPIs principales (tarjetas visuales) en botones que actúen como filtros en cascada al hacerles clic.

### Consideraciones Finales de Dependencias

| Herramienta | Recomendado | Alternativa | Notas |
|-------------|-------------|-------------|-------|
| Gestor Python | `uv` | `pip` | `uv` es 10-100x más rápido |
| Gestor Node.js | `pnpm` | `npm` | `pnpm` evita phantom deps |
| Python target | 3.11+ | — | 3.13 requiere `numpy>=2.1.0` |
| uvicorn dev | `--reload-exclude ".venv"` | — | Evita reinicios infinitos en Windows |
