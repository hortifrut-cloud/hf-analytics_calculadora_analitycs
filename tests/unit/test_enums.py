"""
Archivo: test_enums.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Tests unitarios para las enumeraciones y constantes del dominio (A1.1).
Asegura que los valores de los enums y el orden de las temporadas se
mantengan consistentes, evitando cambios accidentales que puedan romper
la lógica del motor o la persistencia en base de datos.

Acciones Principales:
    - Validación de los valores literales del enum `Productor`.
    - Validación de los valores literales del enum `BloqueKind`.
    - Verificación de la secuencia cronológica de `ALL_SEASONS`.
    - Comprobación de que los enums se comporten como strings (*StrEnum*).

Estructura Interna:
    - `test_productor_values`: Verifica claves de negocio.
    - `test_all_seasons_order`: Garantiza el orden T2627 -> T3132.

Ejecución:
    pytest tests/unit/test_enums.py
"""

from backend.domain.enums import ALL_SEASONS, BloqueKind, Productor


def test_productor_values() -> None:
    assert set(p.value for p in Productor) == {"hf_interna", "hf_terceros", "terceros"}


def test_bloque_kind_values() -> None:
    assert set(b.value for b in BloqueKind) == {
        "crecimiento_hf",
        "recambio_varietal",
        "nuevos_terceros",
    }


def test_all_seasons_order() -> None:
    assert ALL_SEASONS == ["T2627", "T2728", "T2829", "T2930", "T3031", "T3132"]
    assert len(ALL_SEASONS) == 6


def test_productor_is_str() -> None:
    assert isinstance(Productor.HF_INTERNA, str)
    assert Productor.HF_INTERNA == "hf_interna"


def test_bloque_kind_is_str() -> None:
    assert isinstance(BloqueKind.CRECIMIENTO_HF, str)
