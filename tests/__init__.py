"""
Archivo: __init__.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Paquete raíz de la suite de pruebas de la Calculadora de Analytics. Define
la estructura jerárquica de validación del proyecto, integrando desde
pruebas unitarias de bajo nivel hasta simulaciones de flujo de usuario y
validaciones de invariantes de dominio.

Estructura de Pruebas:
    - `unit/`: Validación de lógica pura y funciones de cálculo.
    - `integration/`: Validación de API, Repositorios y Persistencia.
    - `e2e/`: Pruebas de flujo completo con navegador (Playwright).
    - `golden/`: Validación de resultados contra archivos maestros CSV.
    - `property/`: Pruebas de invariantes y lógica basada en propiedades.
    - `simulation/`: Pruebas de simulación de flujos de negocio complejos.
"""
