"""Modelo ORM de la membresía contratada por un socio (app/models/membership.py)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.membership_plan import MembershipPlan

class Membership(Base):
    """Membresía contratada por un socio: un plan durante un periodo.

    start_date, end_date y price_paid se guardan al contratar: el plan 
    se puede editar después sin alterar las membresías ya vendidas.
    Un socio puede tener varias (historial de renovaciones).
    """

    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    socio_id: Mapped[int] = mapped_column(
        ForeignKey("socios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("membership_plans.id"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    plan: Mapped["MembershipPlan"] = relationship()