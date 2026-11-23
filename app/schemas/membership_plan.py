from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator


def _max_two_decimals(value: Decimal) -> bool:
   
    return value.as_tuple().exponent >= -2

class MembershipPlanBase(BaseModel):
    title: str
    description: Optional[str] = None
    cost: Decimal
    duration_months: int
    discount_percent: Decimal = Decimal("0")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: Any) -> str:
        """CA1: El título es obligatorio (máximo 100 caracteres)."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("El título es obligatorio")
        value = value.strip()
        if len(value) > 100:
            raise ValueError("El título no puede exceder 100 caracteres")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: Any) -> Optional[str]:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("cost", mode="after")
    @classmethod
    def validate_cost(cls, value: Decimal) -> Decimal:
        """CA1: El costo debe ser mayor a 0 (máximo 2 decimales)."""
        if not value.is_finite() or value <= 0:
            raise ValueError("El costo debe ser mayor a 0")
        if not _max_two_decimals(value):
            raise ValueError("El costo admite máximo 2 decimales")
        return value

    @field_validator("duration_months", mode="before")
    @classmethod
    def validate_duration(cls, value: Any) -> int:
        """CA1: La duración debe ser un número entero de 1 a 12 meses."""
        if isinstance(value, bool):
            raise ValueError("La duración debe ser un número entero de 1 a 12 meses")
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if not isinstance(value, int) or not 1 <= value <= 12:
            raise ValueError("La duración debe ser un número entero de 1 a 12 meses")
        return value

    @field_validator("discount_percent", mode="after")
    @classmethod
    def validate_discount(cls, value: Decimal) -> Decimal:
        """CA2: El descuento es un porcentaje entre 0 y 100 (máximo 2 decimales)."""
        if not value.is_finite() or value < 0 or value > 100:
            raise ValueError("El descuento debe ser un porcentaje entre 0 y 100")
        if not _max_two_decimals(value):
            raise ValueError("El descuento admite máximo 2 decimales")
        return value

class MembershipPlanCreate(MembershipPlanBase):
    """Schema de entrada para crear un plan."""


class MembershipPlanUpdate(MembershipPlanBase):
    """Schema de entrada para editar un plan (se envían todos los campos)."""


class MembershipPlanResponse(BaseModel):
    """Schema de salida de un plan, incluye el precio final calculado (CA2)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    title: str
    description: Optional[str] = None
    cost: float
    duration_months: int
    discount_percent: float
    final_price: float
    is_active: bool   



    