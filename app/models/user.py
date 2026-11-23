import enum
from typing import List
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"


class User(Base):
    """Modelo ORM que representa a un usuario del sistema."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.MANAGER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relación con gimnasios asignados
    gyms: Mapped[List["Gym"]] = relationship(
        secondary="user_gyms", back_populates="users"
    )