"""Schemas de Pydantic V2 para gestión de usuarios y encargados."""

from typing import List
from pydantic import BaseModel, EmailStr, Field
from app.schemas.auth import GymResponse


class ManagerCreateRequest(BaseModel):
    """Schema de entrada para que el Admin registre un Encargado."""

    email: EmailStr
    password: str = Field(..., min_length=6)
    gym_ids: List[int] = Field(..., min_length=1)


class UserResponse(BaseModel):
    """Schema de salida de usuario (sin contraseñas)."""

    id: int
    email: str
    role: str
    is_active: bool
    gyms: List[GymResponse]

    class Config:
        from_attributes = True