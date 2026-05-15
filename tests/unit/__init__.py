"""
Archivo: __init__.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Paquete de pruebas unitarias del motor de cálculo. Contiene validaciones
atómicas para cada componente lógico del backend, incluyendo el dominio
(inputs/enums) y los bloques de cálculo individuales (B1, B2, B3).

Estructura Interna:
    - `test_inputs`: Validación de esquemas Pydantic.
    - `test_calculos_variedades`: Curvas de producción por edad.
    - `test_crecimiento_hf`: Lógica del Bloque 1.
    - `test_recambio`: Lógica del Bloque 2.
    - `test_nuevos_terceros`: Lógica del Bloque 3.
    - `test_plantines`: Financiamiento de insumos.
    - `test_totales`: Consolidación final de resultados.

Ejecución:
    pytest tests/unit/
"""
