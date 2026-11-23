"""Modelo ORM de los pagos de membresía (SCRUM-17 / GYM-06)."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetodoPago(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


class PagoMembresia(Base):
    """Cada cobro de una membresía: cuánto, cómo, quién cobró y hasta cuándo vale."""

    __tablename__ = "pagos_membresia"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    socio_id: Mapped[int] = mapped_column(
        ForeignKey("socios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    membership_id: Mapped[int] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    monto_plan: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monto_inscripcion: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    metodo_pago: Mapped[MetodoPago] = mapped_column(Enum(MetodoPago), nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)