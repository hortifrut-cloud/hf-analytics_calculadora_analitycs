"""Modelos ORM — SQLAlchemy 2.x Mapped[].

Esquema según description_proyecto.md §1.3.
Usa sqlalchemy.JSON (nunca JSONB) para portabilidad SQLite ↔ Postgres.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

# ---------------------------------------------------------------------------
# Escenario
# ---------------------------------------------------------------------------


class Scenario(Base):
    __tablename__ = "scenario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Perú")
    start_season: Mapped[str] = mapped_column(String(10), nullable=False, default="T2627")
    end_season: Mapped[str] = mapped_column(String(10), nullable=False, default="T3132")
    locked: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)  # SQLite bool
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    base_table_rows: Mapped[list["BaseTableRow"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    base_table_variation: Mapped[list["BaseTableVariation"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    varieties: Mapped[list["Variety"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    rules: Mapped[Optional["Rules"]] = relationship(
        back_populates="scenario", uselist=False, cascade="all, delete-orphan"
    )
    new_project_groups: Mapped[list["NewProjectGroup"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Temporadas
# ---------------------------------------------------------------------------


class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # T2627..T3132
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..5

    scenario: Mapped["Scenario"] = relationship(back_populates="seasons")
    base_table_values: Mapped[list["BaseTableValue"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )
    base_table_variation: Mapped[list["BaseTableVariation"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )
    new_project_ha: Mapped[list["NewProjectHa"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Tabla Base
# ---------------------------------------------------------------------------


class BaseTableRow(Base):
    __tablename__ = "base_table_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="tn")
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scenario: Mapped["Scenario"] = relationship(back_populates="base_table_rows")
    values: Mapped[list["BaseTableValue"]] = relationship(
        back_populates="row", cascade="all, delete-orphan"
    )


class BaseTableValue(Base):
    __tablename__ = "base_table_value"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_table_row_id: Mapped[int] = mapped_column(ForeignKey("base_table_row.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    row: Mapped["BaseTableRow"] = relationship(back_populates="values")
    season: Mapped["Season"] = relationship(back_populates="base_table_values")


class BaseTableVariation(Base):
    __tablename__ = "base_table_variation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scenario: Mapped["Scenario"] = relationship(back_populates="base_table_variation")
    season: Mapped["Season"] = relationship(back_populates="base_table_variation")


# ---------------------------------------------------------------------------
# Variedades
# ---------------------------------------------------------------------------


class Variety(Base):
    __tablename__ = "variety"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scenario: Mapped["Scenario"] = relationship(back_populates="varieties")
    params: Mapped[list["VarietyParam"]] = relationship(
        back_populates="variety", cascade="all, delete-orphan"
    )
    subrows: Mapped[list["NewProjectSubrow"]] = relationship(
        back_populates="variety", cascade="all, delete-orphan"
    )


class VarietyParam(Base):
    __tablename__ = "variety_param"
    __table_args__ = (UniqueConstraint("variety_id", "plant_year", name="uq_variety_plant_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variety_id: Mapped[int] = mapped_column(ForeignKey("variety.id"), nullable=False)
    plant_year: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..7
    productividad: Mapped[float] = mapped_column(Float, nullable=False)
    densidad: Mapped[float] = mapped_column(Float, nullable=False)
    precio_estimado: Mapped[float] = mapped_column(Float, nullable=False)
    pct_recaudacion: Mapped[float] = mapped_column(Float, nullable=False)

    variety: Mapped["Variety"] = relationship(back_populates="params")


# ---------------------------------------------------------------------------
# Reglas / Definiciones
# ---------------------------------------------------------------------------


class Rules(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False, unique=True)
    royaltie_fob: Mapped[float] = mapped_column(Float, nullable=False, default=0.12)
    costo_plantines: Mapped[float] = mapped_column(Float, nullable=False, default=3.5)
    interes_financiamiento: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    financiamiento_anios: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    scenario: Mapped["Scenario"] = relationship(back_populates="rules")


# ---------------------------------------------------------------------------
# Nuevos Proyectos
# ---------------------------------------------------------------------------


class NewProjectGroup(Base):
    __tablename__ = "new_project_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # BloqueKind value

    scenario: Mapped["Scenario"] = relationship(back_populates="new_project_groups")
    subrows: Mapped[list["NewProjectSubrow"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class NewProjectSubrow(Base):
    __tablename__ = "new_project_subrow"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("new_project_group.id"), nullable=False)
    variety_id: Mapped[int] = mapped_column(ForeignKey("variety.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)  # CHAO, OLMOS, Talsa, ...

    group: Mapped["NewProjectGroup"] = relationship(back_populates="subrows")
    variety: Mapped["Variety"] = relationship(back_populates="subrows")
    ha_values: Mapped[list["NewProjectHa"]] = relationship(
        back_populates="subrow", cascade="all, delete-orphan"
    )


class NewProjectHa(Base):
    __tablename__ = "new_project_ha"
    __table_args__ = (UniqueConstraint("subrow_id", "season_id", name="uq_subrow_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subrow_id: Mapped[int] = mapped_column(ForeignKey("new_project_subrow.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    hectareas: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    subrow: Mapped["NewProjectSubrow"] = relationship(back_populates="ha_values")
    season: Mapped["Season"] = relationship(back_populates="new_project_ha")


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scenario.id"), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
