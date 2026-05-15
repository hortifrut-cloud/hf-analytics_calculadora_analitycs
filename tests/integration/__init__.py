"""
Archivo: __init__.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Paquete de pruebas de integración para la Calculadora de Analytics. Valida 
la interacción entre los componentes del backend (API, Repositorios, 
Modelos y Motor de Cálculos), asegurando que el sistema funcione 
correctamente como un todo antes de pasar a la capa de UI.

Contenido del Paquete:
    - `conftest.py`: Infraestructura de cliente de pruebas y DB efímera.
    - `test_api_*.py`: Pruebas de endpoints REST y lógica de negocio vía HTTP.
    - `test_models.py`: Validación de la capa de persistencia ORM.
    - `test_repos.py`: Validación de la capa de acceso a datos y dominio.
    - `test_session.py`: Validación de la configuración de motores SQL.
"""
