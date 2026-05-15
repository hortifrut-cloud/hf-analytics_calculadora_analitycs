"""
Archivo: main.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Punto de entrada para el servidor de ejecución. Re-exporta la instancia de 
la aplicación Starlette para facilitar el despliegue con Uvicorn u otros 
servidores ASGI.

Ejecución:
    uvicorn backend.main:app --reload
"""

from app import app  # noqa: F401
