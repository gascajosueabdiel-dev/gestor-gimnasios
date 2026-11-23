"""Schemas de Pydantic V2 para membresías de socios (app/schemas/membership.py)."""

from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.socio_plan import Membership

MAX_ID = 2_147_483_647


class MembershipCreate(BaseModel):
    """Entrada para asignar un plan a un socio. Las fechas y el precio los calcula el sistema."""

    plan_id: int = Field(..., ge=1, le=MAX_ID)


class MembershipResponse(BaseModel):
    """Membresía de un socio; `vigente` indica si hoy está dentro de su periodo."""

    id: int
    socio_id: int
    plan_id: int
    plan_title: str
    start_date: date
    end_date: date
    price_paid: float
    vigente: bool

    @classmethod
    def build(cls, membresia: "Membership") -> "MembershipResponse":
        """Arma la respuesta; requiere que membresia.plan esté disponible."""
        hoy = date.today()
        return cls(
            id=membresia.id,
            socio_id=membresia.socio_id,
            plan_id=membresia.plan_id,
            plan_title=membresia.plan.title,
            start_date=membresia.start_date,
            end_date=membresia.end_date,
            price_paid=float(membresia.price_paid),
            vigente=membresia.start_date <= hoy <= membresia.end_date,
        )