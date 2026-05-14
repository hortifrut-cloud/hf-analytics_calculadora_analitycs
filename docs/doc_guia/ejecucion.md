# Guía de Ejecución: Timing Agrónomico

> **Proyecto:** `Proyecto_timming_agricola`
> **Fecha:** 2026-04-22

---

## 1. Requisitos Previos

### 1.1 Software

| Software | Versión mínima | Verificar con |
|----------|---------------|---------------|
| Python | 3.11+ | `python --version` |
| uv (Recomendado) | Latest | `uv --version` |
| Node.js | 18+ | `node --version` |
| pnpm | Latest | `pnpm --version` |
| Git | 2.30+ | `git --version` |

### 1.2 Cuentas

- **ShinyApps.io**: Cuenta activa con token configurado
- **rsconnect-python**: `pip install rsconnect-python`

---

## 2. Instalación Local

### 2.1 Preparar entorno de Python

Se recomienda usar **uv** por su velocidad, pero se incluye el método tradicional con **pip**.

#### Opción A: Usando uv (Recomendado 🚀)
```powershell
# Crear entorno e instalar dependencias en un solo paso
uv venv
uv pip install -r requirements.txt

# Para activar (opcional si usas 'uv run')
.\.venv\Scripts\activate
```

#### Opción B: Usando pip tradicional
```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.2 Instalar dependencias del Frontend

```powershell
cd frontend
pnpm install
cd ..
```

### 2.3 Configurar variables de entorno

```powershell
# Copiar ejemplo y editar
Copy-Item .env.example .env
# Editar .env con los valores reales
```

---

## 3. Ejecución en Desarrollo

### 3.1 Opción A: Script automatizado

```powershell
.\scripts\dev.ps1
```

### 3.2 Opción B: Manual (2 terminales)

**Terminal 1 — Backend (FastAPI + Shiny):**
```powershell
# Con uv
uv run python -m uvicorn backend.main:app --reload --port 8000 --reload-exclude ".venv"

# Con pip
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000 --reload-exclude '.venv/*'
```

**Terminal 2 — Frontend (Astro dev server):**
```powershell
cd frontend
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process #Solo la primera vez que se ejecuta en la terminal
pnpm run dev

```

### 3.3 Acceder

- **Frontend Astro**: http://localhost:4321
- **API directa**: http://localhost:8000/api/status
- **Dashboard Shiny**: http://localhost:8000/shiny/

### 3.4 Checklist de Verificación Rápida

Para confirmar que todo funciona:
1. [ ] Entrar a `localhost:4321` y ver que cargan los KPIs.
2. [ ] Cambiar un filtro (Zona/Fundo) y ver que la tabla Gantt se actualiza.
3. [ ] Desplegar el Iframe de Shiny y verificar que carga el gráfico de Plotly.
4. [ ] Verificar que la API responde en `localhost:8000/api/status`.

---

## 4. Compilación para Producción

### 4.1 Build del frontend

```powershell
cd frontend
pnpm run build
cd ..
```

### 4.2 Copiar estáticos al backend

```powershell
# Crear directorio si no existe
New-Item -ItemType Directory -Path backend\static -Force

# Copiar archivos compilados de Astro
Copy-Item -Path frontend\dist\* -Destination backend\static\ -Recurse -Force
```

### 4.3 Verificar build local

```powershell
# Ejecutar FastAPI sirviendo todo unificado
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --port 8000
```

Acceder a http://localhost:8000 — debe mostrar la app completa (Astro + API + Shiny).

---

## 5. Despliegue en ShinyApps.io

### 5.1 Pre-vuelo

> [!IMPORTANT]
> **Siempre** recompila el frontend antes de desplegar. Si omites este paso,
> se subirá una versión antigua del HTML/CSS/JS y la app se verá diferente a la local.
>
> El `astro.config.mjs` está configurado con `inlineStylesheets: 'always'` para que
> el CSS y JS se embeben directamente en el HTML. Esto evita problemas de rutas
> absolutas (`/_astro/...`) que no funcionan en ShinyApps.io (subpath `/timing-agronomico/`).

```powershell
# Antes de ejecutar los comandos, ejecutar el script de inicio
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 1. Activar el entorno (en Windows)
.\.venv\Scripts\Activate.ps1

# 2. Recompilar el frontend de Astro (CSS se inlinea, JS queda externo)
cd frontend
pnpm run build
cd ..

# 3. Post-procesar: inyectar JS inline y corregir rutas de favicon
python scripts\inline_js.py

# 4. Copiar archivos compilados al directorio estático del backend
xcopy /E /Y frontend\dist\* backend\static\

# 5. Verificar que .rscignore excluya lo necesario
Get-Content .rscignore

# 6. Verificar requirements.txt esté actualizado
pip freeze > requirements.txt
```

### 5.2 Configurar cuenta (usando variables de .env)

Asegúrate de que tu archivo `.env` tenga los valores correctos para `rsconnect_usuario`, `rsconnect_token`, etc. 

En PowerShell, puedes cargar las variables y configurar la cuenta así:

```powershell
# Cargar variables del .env (PowerShell)
Get-Content .env | Foreach-Object {
    if ($_ -match "^(?<name>[^#\s=]+)=(?<value>.*)$") {
        $env:$($Matches.name) = $Matches.value.Trim('"')
    }
}

# Registrar la cuenta en rsconnect (Bypass Acceso Denegado)
python -c "from rsconnect.main import cli; cli()" add --account $env:rsconnect_usuario --name $env:rsconnect_name --token $env:rsconnect_token --secret $env:rsconnect_secret
```

### 5.3 Primer Despliegue

La primera vez que subas la aplicación, usa `--new` para forzar una creación limpia.

> **Nota:** El `app.py` usa Starlette (la base de Shiny for Python) en lugar de FastAPI,
> porque ShinyApps.io no soporta el modo `python-fastapi`. Los endpoints API se
> reimplementan como funciones Starlette puras, manteniendo la misma funcionalidad.

```powershell
# Desplegar por primera vez (--new fuerza creación limpia)
python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name alex-prieto --title "Timing-Agronomico" --new
```


### 5.4 Actualizaciones (Redeploy)

Una vez que la aplicación ya existe en ShinyApps.io, `rsconnect` guarda los metadatos en una carpeta local. Para subir cambios (código, estilos, etc.), solo necesitas ejecutar:

```powershell
# Opción A: Re-desplegar usando los metadatos guardados
python -c "from rsconnect.main import cli; cli()" deploy shiny .

# Opción B: Si quieres estar seguro de sobreescribir la app específica
python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name alex-prieto --app-id 17216330

uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name alex-prieto --app-id 17216330
```

> [!TIP]
> Si alguna vez pierdes los metadatos locales pero quieres actualizar la misma app, puedes usar el flag `--app-id <ID_DE_TU_APP>` que aparece en el dashboard de ShinyApps.io.

### 5.5 Verificación post-despliegue

- [ ] URL pública accesible
- [ ] Gantt se renderiza con datos
- [ ] Filtros funcionan
- [ ] KPIs muestran valores correctos
- [ ] Semana actual visible (línea roja)
- [ ] Iframe de Shiny carga
- [ ] Recarga de página NO da error 404

---

## 6. Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| 404 al recargar | Multi-página en Astro | Verificar que todo sea SPA |
| Fetch falla en producción | URLs absolutas | Cambiar a URLs relativas (`./api/`) |
| Shiny no carga en iframe | WebSocket bloqueado | Verificar middleware de sanitización |
| Datos no aparecen | CSV no encontrado | Verificar ruta en `engine.py` |
| Build de Astro falla | Node.js desactualizado | Actualizar a Node 18+ |

---

## 7. Tests

```powershell
# Ejecutar todos los tests
.\.venv\Scripts\Activate.ps1
pytest test/ -v

# Solo tests del engine
pytest test/test_engine.py -v

# Solo tests de la API
pytest test/test_api.py -v
```
