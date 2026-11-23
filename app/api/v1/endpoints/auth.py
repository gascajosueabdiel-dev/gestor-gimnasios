"""Endpoints de FastAPI para autenticación y registro de usuarios."""

from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, oauth2_scheme, verify_gym_access
from app.core.config import settings
from app.schemas.socio import GimnasioActivoRequest
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.gym import Gym
from app.schemas.auth import (
    LoginRequest,
    Token,
    AdminRegisterRequest,
    AdminRegisterResponse,
    GymResponse,
)

router = APIRouter()


@router.post(
    "/register-admin",
    response_model=AdminRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_admin(request: AdminRegisterRequest, db: Session = Depends(get_db)):
    """
    Endpoint para registrar un Administrador y crear su Gimnasio.

    Criterios de Aceptacion:
    - CA1: Validacion automatica de campos obligatorios (nombre max 100 car).
    - CA2: Monto de inscripcion base valido (>= 0, max 2 decimales).
    - CA3: Verificacion de correo unico; responde 409 si ya existe.
    - CA4: Vincula admin con gimnasio y guarda contrasena cifrada con Argon2.
    """
    existing_user_stmt = select(User).where(User.email == request.email)
    if db.scalars(existing_user_stmt).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        )

    new_gym = Gym(
        name=request.gym_name,
        location=request.location,
        logo_url=request.logo_url,
        base_enrollment_fee=float(request.base_enrollment_fee),
        is_active=True,
    )
    db.add(new_gym)
    db.flush()

    hashed_pwd = get_password_hash(request.password)
    new_admin = User(
        email=request.email,
        hashed_password=hashed_pwd,
        role=UserRole.ADMIN,
        is_active=True,
    )

    new_admin.gyms.append(new_gym)
    db.add(new_admin)

    db.commit()
    db.refresh(new_admin)
    db.refresh(new_gym)

    return AdminRegisterResponse(
        user_id=new_admin.id,
        email=new_admin.email,
        role=new_admin.role.value,
        gym=GymResponse.model_validate(new_gym),
    )


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint para autenticar usuarios y obtener token JWT.

    Cumple con Criterio de Aceptacion 1:
    - Credenciales validas: Retorna JWT con expiracion a 60 minutos.
    - Credenciales invalidas: Retorna HTTP 401 'Correo o contrasena incorrectos'.
    """
    stmt = select(User).where(User.email == request.email)
    user = db.scalars(stmt).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo"
        )

    gym_ids = [gym.id for gym in user.gyms]

    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "role": user.role.value,
        "gym_ids": gym_ids,
    }

    access_token = create_access_token(data=payload)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/active-gym", response_model=Token)
def change_active_gym(
    request: GimnasioActivoRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SCRUM-14 CA3: Cambia el gimnasio activo y devuelve un token nuevo.
    - Aplica las reglas de verify_gym_access (403 si no tiene acceso).
    - Conserva la expiracion original: cambiar de gimnasio no alarga la sesion.
    """
    verify_gym_access(gym_id=request.gym_id, current_user=current_user)
    if db.get(Gym, request.gym_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gimnasio no encontrado",
        )

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    expira = datetime.fromtimestamp(payload.pop("exp"), timezone.utc)
    payload["active_gym_id"] = request.gym_id
    access_token = create_access_token(
        data=payload, expires_delta=expira - datetime.now(timezone.utc)
    )
    return Token(access_token=access_token, token_type="bearer")