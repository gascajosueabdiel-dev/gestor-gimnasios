
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role, verify_gym_access
from app.models.gym import Gym
from app.models.membership_plan import MembershipPlan
from app.models.user import User, UserRole
from app.schemas.membership_plan import (
    MembershipPlanCreate,
    MembershipPlanUpdate,
    MembershipPlanResponse,
)

router = APIRouter()


def _get_active_gym(db: Session, gym_id: int) -> Gym:
    gym = db.scalars(select(Gym).where(Gym.id == gym_id)).first()
    if not gym or not gym.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gimnasio no encontrado o inactivo",
        )
    return gym

@router.get("/{gym_id}/plans", response_model=List[MembershipPlanResponse])
def list_plans(
    gym_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista los planes del gimnasio indicado.

    - CA4: Solo devuelve los planes que pertenecen a ese gimnasio activo.
    - Admin y Encargado pueden consultar (el Encargado solo sus gimnasios asignados).
    """
    verify_gym_access(gym_id=gym_id, current_user=current_user)
    _get_active_gym(db, gym_id)

    stmt = (
        select(MembershipPlan)
        .where(MembershipPlan.gym_id == gym_id, MembershipPlan.is_active.is_(True))
        .order_by(MembershipPlan.id)
    )
    plans = db.scalars(stmt).all()
    return [MembershipPlanResponse.model_validate(plan) for plan in plans]

@router.post(
    "/{gym_id}/plans",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    gym_id: int,
    request: MembershipPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Crea un plan de membresía en el gimnasio indicado.

    - CA1/CA2: Validaciones de título, costo, duración y descuento (HTTP 422).
    - CA3: Solo ADMIN; un Encargado recibe 403 Forbidden.
    - CA4: El plan queda ligado al gimnasio.
    """
    verify_gym_access(gym_id=gym_id, current_user=current_user)
    _get_active_gym(db, gym_id)

    plan = MembershipPlan(gym_id=gym_id, **request.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return MembershipPlanResponse.model_validate(plan)

@router.put("/{gym_id}/plans/{plan_id}", response_model=MembershipPlanResponse)
def update_plan(
    gym_id: int,
    plan_id: int,
    request: MembershipPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Edita un plan existente del gimnasio indicado.

    - CA3: Solo ADMIN; un Encargado recibe 403 Forbidden.
    - CA4: Responde 404 si el plan no pertenece a ese gimnasio.
    """
    verify_gym_access(gym_id=gym_id, current_user=current_user)
    _get_active_gym(db, gym_id)

    stmt = select(MembershipPlan).where(
        MembershipPlan.id == plan_id, MembershipPlan.gym_id == gym_id
    )
    plan = db.scalars(stmt).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado en este gimnasio",
        )

    for field, value in request.model_dump().items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return MembershipPlanResponse.model_validate(plan)