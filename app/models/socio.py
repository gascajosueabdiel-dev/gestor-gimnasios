from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.socio_plan import Membership
from app.models.membership_plan import MembershipPlan
from app.schemas.socio_plan import MembershipCreate, MembershipResponse

class Socio(Base):
    """Modelo ORM de un socio, vinculado al gimnasio donde se registró."""

    __tablename__ = "socios"
    __table_args__ = (UniqueConstraint("gym_id", "num_referencia_unico"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    gym_id: Mapped[int] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    num_referencia_unico: Mapped[int] = mapped_column(nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    celular: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_nacimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    metas: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)


class ContadorSocios(Base):
    """Último número de referencia entregado en cada gimnasio.

    Va en una tabla propia para no modificar el modelo Gym: así no hay que
    borrar la base de datos existente para agregar esta historia.
    """

    __tablename__ = "contador_socios"

    gym_id: Mapped[int] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), primary_key=True
    )
    ultimo_numero: Mapped[int] = mapped_column(nullable=False)
