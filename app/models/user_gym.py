from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class UserGym(Base):
    """Tabla asociativa M:N entre Usuarios y Gimnasios."""

    __tablename__ = "user_gyms"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    gym_id: Mapped[int] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), primary_key=True
    )