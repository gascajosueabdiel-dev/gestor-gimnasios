"""Endpoints protegidos para gestión de gimnasios."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, verify_gym_access
from app.models.gym import Gym
from app.models.user import User
from app.schemas.auth import GymResponse

router = APIRouter()


@router.get("/{gym_id}", response_model=GymResponse)
def get_gym_detail(
    gym_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Consulta los detalles de un gimnasio específico.

    Cumple con:
    - CA4: Valida token ausente/expirado (HTTP 401).
    - CA2: Valida acceso asignado por gimnasio (HTTP 403 si no pertenece al usuario).
    """
    # Verificación de acceso al gimnasio (CA2)
    verify_gym_access(gym_id=gym_id, current_user=current_user)

    stmt = select(Gym).where(Gym.id == gym_id)
    gym = db.scalars(stmt).first()

    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gimnasio no encontrado",
        )

    return GymResponse.model_validate(gym)