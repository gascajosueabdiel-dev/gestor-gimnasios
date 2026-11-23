"""Dependencias de FastAPI para inyección de base de datos y autorización RBAC."""

from typing import Generator, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.gym import Gym
from app.models.user import User, UserRole

# Extractor del esquema Bearer JWT desde el encabezado Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator:
    """Generador de sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    CA4: Verifica el token de acceso JWT.
    Retorna 401 si el token falta, expiro o es invalido.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    user = db.scalars(stmt).first()

    if not user or not user.is_active:
        raise credentials_exception

    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Verifica que el usuario autenticado posea uno de los roles autorizados.
    Retorna 403 Forbidden si el rol no coincide.
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta acción",
            )
        return current_user

    return role_checker


def verify_gym_access(
    gym_id: int, current_user: User = Depends(get_current_user)
) -> None:
    """
    CA2: Control de acceso multisede por gimnasio.
    - Administrador (ADMIN): Acceso global.
    - Encargado (MANAGER): Retorna 403 Forbidden si accede a un gimnasio no asignado.
    """
    if current_user.role == UserRole.ADMIN:
        return

    assigned_gym_ids = [gym.id for gym in current_user.gyms]
    if gym_id not in assigned_gym_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso asignado a este gimnasio",
        )


def get_active_gym(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Gym:
    """
    SCRUM-14 CA3: Gimnasio activo del usuario, tomado del token.
    - Usa el claim "active_gym_id"; si el token no lo trae (por ejemplo, uno
      emitido por /auth/login), usa el primer gimnasio asignado.
    - Aplica las mismas reglas de acceso que verify_gym_access.
    """
    # get_current_user ya validó firma y expiración del token.
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    gym_id = payload.get("active_gym_id")
    if gym_id is None:
        gym_id = min((gym.id for gym in current_user.gyms), default=None)
    if gym_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene gimnasios asignados",
        )

    verify_gym_access(gym_id=gym_id, current_user=current_user)

    gym = db.get(Gym, gym_id)
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gimnasio no encontrado",
        )
    return gym