"""
Archivo: __init__.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Paquete de la API REST para la Calculadora de Analytics. Define los contratos de
entrada/salida y los handlers para la gestión de escenarios y proyecciones.

Estructura del Paquete:
    - `schemas.py`: DTOs de Pydantic.
    - `routes.py`: Definición de endpoints Starlette.
    - `errors.py`: Manejo de excepciones HTTP.
    - `scenarios.py`, `varieties.py`, `rules.py`, `new_projects.py`: Handlers funcionales.
    - `recompute.py`: Motor de disparo de cálculos.
    - `exports.py`: Generación de reportes Excel.

Ejemplo de Integración:
    from backend.api.routes import api_routes
    app = Starlette(routes=api_routes)
"""
