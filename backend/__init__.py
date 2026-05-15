"""
Archivo: __init__.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Paquete principal del backend para la Calculadora de Analytics. Organiza la 
arquitectura en capas (Dominio, DB, Lógica, API y UI Reactiva) para 
garantizar la mantenibilidad y escalabilidad del sistema.

Estructura del Proyecto:
    - `domain/`: Modelos de negocio puros (inputs/outputs).
    - `db/`: Capa de persistencia (ORM y Repositorios).
    - `logic/`: Motores de cálculo y algoritmos.
    - `api/`: Endpoints REST y contratos de datos.
    - `shiny_app/`: Interfaz de usuario reactiva.
"""
