from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Attendance(Base):
    """Modelo ORM que registra la asistencia de un socio a un gimnasio."""

    __tablename__ = "member_attendances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("socios.id"), nullable=False, index=True
    )
    gym_id: Mapped[int] = mapped_column(
        ForeignKey("gyms.id"), nullable=False, index=True
    )
    date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relaciones (para acceder a los objetos completos desde Python)
    socio: Mapped["Socio"] = relationship()
    gimnasio: Mapped["Gym"] = relationship()