# scripts/dev.ps1 — Arranca backend (Starlette+Shiny) y frontend (Astro) en paralelo
$root = Split-Path -Parent $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root'; uv run python -m uvicorn app:app --reload --port 8000 --reload-exclude '.venv'"

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\frontend'; pnpm run dev"

Write-Host "Backend  -> http://localhost:8000"
Write-Host "Frontend -> http://localhost:4321"
Write-Host "Shiny    -> http://localhost:8000/shiny/"
