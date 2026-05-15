# scripts/build.ps1 — Pipeline de build: Astro → post-proceso → backend/static
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Set-Location $root
Write-Host "=== Build HF Breeding Planner ===" -ForegroundColor Cyan

# 1. Compilar Astro
Write-Host "`n[1/3] Compilando Astro (pnpm run build)..." -ForegroundColor Yellow
Set-Location "$root\frontend"
pnpm run build
if (-not $?) { Write-Error "pnpm build falló"; exit 1 }
Set-Location $root

# 2. Post-procesar: inyectar JS inline y corregir rutas absolutas
Write-Host "`n[2/3] Post-procesando index.html (inline_js.py)..." -ForegroundColor Yellow
uv run python scripts/inline_js.py
if (-not $?) { Write-Error "inline_js.py falló"; exit 1 }

# 3. Copiar estáticos compilados al backend
Write-Host "`n[3/3] Copiando frontend\dist\ -> backend\static\..." -ForegroundColor Yellow
if (-not (Test-Path "$root\backend\static")) {
    New-Item -ItemType Directory -Path "$root\backend\static" -Force | Out-Null
}
Copy-Item -Path "$root\frontend\dist\*" -Destination "$root\backend\static\" -Recurse -Force

Write-Host "`n=== Build completado. Levanta el servidor con: ===" -ForegroundColor Green
Write-Host "  uv run python -m uvicorn app:app --port 8000" -ForegroundColor Green
Write-Host "  -> http://localhost:8000/" -ForegroundColor Green
