"""Endpoints protegidos para administración de usuarios."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.security import get_password_hash
from app.models.gym import Gym
from app.models.user import User, UserRole
from app.schemas.user import ManagerCreateRequest, UserResponse

router = APIRouter()


@router.post(
    "/managers",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manager(
    request: ManagerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Registra un Encargado (MANAGER) y lo asigna a uno o más gimnasios.

    Cumple con CA3:
    - Solo accesible por ADMIN (retorna 403 si un MANAGER lo intenta).
    - Asigna 1 o más gimnasios existentes.
    """
    # 1. Verificar si el correo ya existe
    stmt_user = select(User).where(User.email == request.email)
    if db.scalars(stmt_user).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        )

    # 2. Consultar y validar que todos los gym_ids existan
    stmt_gyms = select(Gym).where(Gym.id.in_(request.gym_ids))
    gyms = db.scalars(stmt_gyms).all()

    if len(gyms) != len(set(request.gym_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más gimnasios indicados no existen",
        )

    # 3. Crear usuario con rol MANAGER y contraseña cifrada con Argon2
    hashed_pwd = get_password_hash(request.password)
    new_manager = User(
        email=request.email,
        hashed_password=hashed_pwd,
        role=UserRole.MANAGER,
        is_active=True,
    )

    # 4. Asignar los gimnasios a la relación M:N
    new_manager.gyms.extend(gyms)

    db.add(new_manager)
    db.commit()
    db.refresh(new_manager)

    return UserResponse.model_validate(new_manager)