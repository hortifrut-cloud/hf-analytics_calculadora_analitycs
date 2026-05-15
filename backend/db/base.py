"""
Archivo: base.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Define la clase base declarativa para el mapeo ORM de SQLAlchemy. Sirve como 
punto de anclaje para todos los modelos del sistema.

Estructura Interna:
    - `Base`: Clase base que hereda de `DeclarativeBase`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
