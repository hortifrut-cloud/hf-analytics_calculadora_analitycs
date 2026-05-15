from backend.domain.enums import ALL_SEASONS, BloqueKind
from backend.domain.inputs import NewProjectCell
from backend.logic.lag_matrix import aggregate_ha, build_lag_matrix

SEASONS = ALL_SEASONS


# A2.3.1 — build_lag_matrix
def test_lag_m1_t2728_uses_t2627() -> None:
    ha = {"T2627": 100.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    assert df.loc[1, "T2728"] == 100.0


def test_lag_m1_t2829_uses_t2728() -> None:
    ha = {"T2728": 50.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    assert df.loc[1, "T2829"] == 50.0


def test_lag_m2_t2829_uses_t2627() -> None:
    ha = {"T2627": 100.0, "T2728": 50.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    assert df.loc[2, "T2829"] == 100.0


def test_lag_m5_t3132_uses_t2627() -> None:
    # Año5 at T3132: index(T3132)=5, 5-5=0 → T2627
    ha = {"T2627": 250.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    assert df.loc[5, "T3132"] == 250.0


def test_lag_m4_t3132_uses_t2728() -> None:
    # Año4 at T3132: index 5-4=1 → T2728
    ha = {"T2728": 200.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    assert df.loc[4, "T3132"] == 200.0


def test_lag_zero_outside_range() -> None:
    ha = {"T2627": 100.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    # T2627 itself: no Año n can place it (would require ha at T2627 - n which is before start)
    assert df.loc[1, "T2627"] == 0.0


def test_lag_chao_olmos_combined() -> None:
    # imagen7: CHAO=250@T2627, OLMOS=200@T2728
    ha = {"T2627": 250.0, "T2728": 200.0}
    df = build_lag_matrix(ha, max_plant_year=5)
    # Año1 T2728: CHAO ha from T2627 = 250
    assert df.loc[1, "T2728"] == 250.0
    # Año1 T2829: OLMOS ha from T2728 = 200
    assert df.loc[1, "T2829"] == 200.0
    # Año2 T2829: CHAO ha from T2627 = 250
    assert df.loc[2, "T2829"] == 250.0


# A2.3.2 — aggregate_ha
def test_aggregate_ha_b1() -> None:
    cells = [
        NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="CHAO",
            variety_name="V1",
            season="T2627",
            hectareas=250,
        ),
        NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="OLMOS",
            variety_name="V1",
            season="T2728",
            hectareas=200,
        ),
    ]
    agg = aggregate_ha(cells, BloqueKind.CRECIMIENTO_HF, "V1")
    assert agg["T2627"] == 250.0
    assert agg["T2728"] == 200.0
    assert agg["T2829"] == 0.0


def test_aggregate_ha_b3_sums_subproyectos() -> None:
    # imagen9: Talsa@T2627=100, Diamond Bridge@T2627=25 → T2627=125
    cells = [
        NewProjectCell(
            bloque=BloqueKind.NUEVOS_TERCEROS,
            sub_proyecto="Talsa",
            variety_name="V1",
            season="T2627",
            hectareas=100,
        ),
        NewProjectCell(
            bloque=BloqueKind.NUEVOS_TERCEROS,
            sub_proyecto="Diamond Bridge",
            variety_name="V1",
            season="T2627",
            hectareas=25,
        ),
        NewProjectCell(
            bloque=BloqueKind.NUEVOS_TERCEROS,
            sub_proyecto="Talsa",
            variety_name="V1",
            season="T2728",
            hectareas=100,
        ),
    ]
    agg = aggregate_ha(cells, BloqueKind.NUEVOS_TERCEROS, "V1")
    assert agg["T2627"] == 125.0
    assert agg["T2728"] == 100.0


def test_aggregate_ha_filters_bloque() -> None:
    cells = [
        NewProjectCell(
            bloque=BloqueKind.CRECIMIENTO_HF,
            sub_proyecto="CHAO",
            variety_name="V1",
            season="T2627",
            hectareas=250,
        ),
        NewProjectCell(
            bloque=BloqueKind.RECAMBIO_VARIETAL,
            sub_proyecto="OLMOS",
            variety_name="V1",
            season="T2627",
            hectareas=50,
        ),
    ]
    agg = aggregate_ha(cells, BloqueKind.RECAMBIO_VARIETAL, "V1")
    assert agg["T2627"] == 50.0
