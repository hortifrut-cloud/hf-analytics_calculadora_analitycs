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
