from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy import String, Text, Boolean, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    gym_id: Mapped[int] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)



    gym: Mapped["Gym"] = relationship(back_populates="plans")

    @property
    def final_price(self) -> Decimal:
        cost = Decimal(str(self.cost))
        discount = Decimal(str(self.discount_percent or 0))
        final = cost * (Decimal("100") - discount) / Decimal("100")
        return final.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
