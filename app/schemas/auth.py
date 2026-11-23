"""Schemas de Pydantic V2 para autenticación y gestión de tokens."""

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema para recibir las credenciales de inicio de sesión."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema para responder con el Token JWT generado."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema del contenido descodificado del token."""

    sub: Optional[str] = None
    user_id: int
    role: str
    gym_ids: List[int]


class AdminRegisterRequest(BaseModel):
    """Schema de entrada para registro de Administrador y alta de su Gimnasio."""

    email: EmailStr
    password: str = Field(..., min_length=6)
    gym_name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = None
    logo_url: Optional[str] = None
    base_enrollment_fee: Decimal = Field(..., ge=0)

    @field_validator("base_enrollment_fee", mode="after")
    @classmethod
    def validate_enrollment_fee(cls, value: Decimal) -> Decimal:
        """Validacion de CA2: Monto mayor o igual a 0 con maximo 2 decimales."""
        if value < 0 or value.as_tuple().exponent < -2:
            raise ValueError("Monto inválido")
        return value


class GymResponse(BaseModel):
    """Schema de salida para la información del gimnasio."""

    id: int
    name: str
    location: Optional[str] = None
    logo_url: Optional[str] = None
    base_enrollment_fee: float

    class Config:
        from_attributes = True


class AdminRegisterResponse(BaseModel):
    """Schema de salida del registro de administrador."""

    user_id: int
    email: str
    role: str
    gym: GymResponse