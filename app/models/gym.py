from typing import List, Optional
from sqlalchemy import String, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Gym(Base):
    """Modelo ORM que representa un Gimnasio o sucursal."""

    __tablename__ = "gyms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    base_enrollment_fee: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relacion muchos a muchos con usuarios
    users: Mapped[List["User"]] = relationship(
        secondary="user_gyms", back_populates="gyms"
    )

    
    # Relación uno a muchos con planes de membresía (SCRUM-49)
    plans: Mapped[List["MembershipPlan"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )