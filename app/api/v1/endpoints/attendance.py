"""Endpoints protegidos para gestión de asistencias (Recepción)."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_active_gym, get_db, require_role
from app.models.attendance import Attendance
from app.models.gym import Gym
from app.models.socio_plan import Membership
from app.models.socio import Socio
from app.models.user import User, UserRole
from app.schemas.attendance import AttendanceCreateRequest, AttendanceResponse

router = APIRouter()


def tiene_membresia_activa(db: Session, socio: Socio) -> bool:
    """CA2: indica si el socio tiene una membresía vigente hoy.

    Vigente = existe una fila en memberships con start_date <= hoy <= end_date.
    Un socio que nunca ha contratado un plan también cuenta como sin membresía.
    """
    hoy = date.today()
    return db.scalar(
        select(
            exists().where(
                Membership.socio_id == socio.id,
                Membership.start_date <= hoy,
                Membership.end_date >= hoy,
            )
        )
    )


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_attendance(
    request: AttendanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.MANAGER])),
    gym: Gym = Depends(get_active_gym),
):
    """
    Registra la entrada de un socio al gimnasio activo del Encargado.

    Criterios de Aceptación:
    - CA1: con un número de referencia existente guarda fecha y hora de entrada
      (la pone la BD) y devuelve el nombre del socio.
    - CA2: si la membresía está vencida responde 409 con código MEMBRESIA_VENCIDA
      y NO guarda nada; el Encargado decide y, si acepta, el cliente repite la
      petición con permitir_membresia_vencida=true.
    - CA3: si el número no existe en el gimnasio responde 404 "Socio no encontrado"
      y no guarda ningún registro.
    """
    # 1. Buscar al socio por número de referencia, solo dentro del gimnasio activo
    socio = db.scalar(
        select(Socio).where(
            Socio.gym_id == gym.id,
            Socio.num_referencia_unico == request.num_referencia,
        )
    )
    if socio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Socio no encontrado",
        )

    # 2. Membresía vencida: avisar y esperar la decisión del Encargado
    if not request.permitir_membresia_vencida and not tiene_membresia_activa(db, socio):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "codigo": "MEMBRESIA_VENCIDA",
                "mensaje": "Membresía vencida",
                "socio_nombre": socio.nombre,
            },
        )

    # 3. Guardar la entrada
    asistencia = Attendance(member_id=socio.id, gym_id=gym.id)
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)

    return AttendanceResponse.build(asistencia, socio)


@router.get("/recent", response_model=List[AttendanceResponse])
def recent_attendances(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.MANAGER])),
    gym: Gym = Depends(get_active_gym),
):
    """Últimas entradas del gimnasio activo (alimenta la tabla de Recepción)."""
    stmt = (
        select(Attendance)
        .options(joinedload(Attendance.socio))
        .where(Attendance.gym_id == gym.id)
        .order_by(Attendance.date_time.desc(), Attendance.id.desc())
        .limit(limit)
    )
    return [AttendanceResponse.build(a, a.socio) for a in db.scalars(stmt).all()]