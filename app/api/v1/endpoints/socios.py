"""Endpoints de SCRUM-14: registrar socio con número de referencia."""

from typing import List
import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import or_, select, func
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_active_gym, get_db
from app.models.gym import Gym
from app.models.socio import ContadorSocios, Socio
from app.schemas.socio import SocioCreate, SocioResponse

# Imports para obtener lista de asistencia
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceResponse

# Importa para registrar membresía
from app.models.socio_plan import Membership
from app.models.membership_plan import MembershipPlan
from app.schemas.socio_plan import MembershipCreate, MembershipResponse

router = APIRouter()

# Mayor entero que cabe en la columna INTEGER de PostgreSQL.
MAX_ID = 2_147_483_647


def siguiente_num_referencia(db: Session, gym_id: int) -> int:
    """
    CA2: Siguiente número de referencia del gimnasio.

    Un solo INSERT ... ON CONFLICT DO UPDATE ... RETURNING: con altas
    simultáneas, la base las forma en fila y cada una recibe un número
    distinto. Si el alta falla, el incremento se revierte con ella.
    Funciona en SQLite (desarrollo) y PostgreSQL (producción).
    """
    insertar = (
        postgresql.insert
        if db.get_bind().dialect.name == "postgresql"
        else sqlite.insert
    )
    stmt = (
        insertar(ContadorSocios)
        .values(gym_id=gym_id, ultimo_numero=1)
        .on_conflict_do_update(
            index_elements=[ContadorSocios.gym_id],
            set_={"ultimo_numero": ContadorSocios.ultimo_numero + 1},
        )
        .returning(ContadorSocios.ultimo_numero)
    )
    return db.scalar(stmt)


def obtener_socio(db: Session, socio_id: int, gym_id: int) -> Socio:
    """CA3: 404 también para socios de otro gimnasio, para no revelar que existen."""
    socio = db.scalar(
        select(Socio).where(Socio.id == socio_id, Socio.gym_id == gym_id)
    )
    if socio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Socio no encontrado",
        )
    return socio


@router.post("", response_model=SocioResponse, status_code=status.HTTP_201_CREATED)
def registrar_socio(
    request: SocioCreate,
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """
    Registra un socio en el gimnasio activo del usuario.

    Criterios de Aceptacion:
    - CA1: Nombre (max 100) y celular (10 digitos) obligatorios, error por campo.
    - CA2: Numero de referencia automatico y unico dentro del gimnasio.
    - CA3: El socio queda asociado solo al gimnasio activo.
    """
    socio = Socio(
        **request.model_dump(),
        gym_id=gym.id,
        num_referencia_unico=siguiente_num_referencia(db, gym.id),
    )
    db.add(socio)
    db.commit()
    db.refresh(socio)
    return socio


@router.get("", response_model=List[SocioResponse])
def buscar_socios(
    search: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """
    CA4: Busca socios del gimnasio activo por parte del nombre (sin distinguir
    mayúsculas) o por número de referencia exacto. Sin término, lista todos.
    """
    consulta = select(Socio).where(Socio.gym_id == gym.id)
    termino = search.strip()
    if termino:
        condicion = Socio.nombre.icontains(termino, autoescape=True)
        # Hasta 9 dígitos siempre caben en la columna entera de la base.
        if termino.isascii() and termino.isdigit() and len(termino) <= 9:
            condicion = or_(condicion, Socio.num_referencia_unico == int(termino))
        consulta = consulta.where(condicion)
    return db.scalars(
        consulta.order_by(Socio.nombre, Socio.id).limit(limit).offset(offset)
    ).all()


@router.get("/{socio_id}", response_model=SocioResponse)
def consultar_ficha(
    socio_id: int = Path(le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """CA4: Ficha del socio, con fecha de nacimiento y metas."""
    return obtener_socio(db, socio_id, gym.id)


@router.put("/{socio_id}", response_model=SocioResponse)
def actualizar_socio(
    request: SocioCreate,
    socio_id: int = Path(le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """Actualiza los datos del socio. El número de referencia no cambia."""
    socio = obtener_socio(db, socio_id, gym.id)
    for campo, valor in request.model_dump().items():
        setattr(socio, campo, valor)
    db.commit()
    db.refresh(socio)
    return socio

# Endpoint para obtener lista de asistencia del socio en orden descendente.
@router.get("/{socio_id}/asistencias", response_model=List[AttendanceResponse])
def historial_asistencias(
    socio_id: int = Path(le=MAX_ID),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """
    CA4: Últimas entradas del socio, de la más reciente a la más antigua.
    """

    socio = obtener_socio(db, socio_id, gym.id)
    asistencias = db.scalars(
        select(Attendance)
        .where(Attendance.member_id == socio.id, Attendance.gym_id == gym.id)
        # El id desempata si dos entradas caen en el mismo instante
        .order_by(Attendance.date_time.desc(), Attendance.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [AttendanceResponse.build(a, socio) for a in asistencias]

# Funciones para registrar membresía
def _sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses calendario; si el día no existe (31 -> febrero) usa el último del mes."""
    total = fecha.month - 1 + meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)
 
@router.post(
    "/{socio_id}/membresias",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def asignar_membresia(
    request: MembershipCreate,
    socio_id: int = Path(le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """
    Asigna un plan de membresía a un socio del gimnasio activo.
 
    - 404 si el socio es de otro gimnasio (igual que obtener_socio).
    - 404 si el plan no existe, es de otro gimnasio o ya no se ofrece (is_active).
    - La vigencia y el precio se calculan aquí y se guardan: editar el plan después
      no cambia las membresías ya vendidas.
    """
    socio = obtener_socio(db, socio_id, gym.id)
 
    plan = db.scalar(
        select(MembershipPlan).where(
            MembershipPlan.id == request.plan_id,
            MembershipPlan.gym_id == gym.id,
            MembershipPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado en este gimnasio",
        )
 
    # Si el socio aún tiene membresía vigente, la nueva empieza al día siguiente de que
    # termine la última.
    hoy = date.today()
    ultimo_fin = db.scalar(
        select(func.max(Membership.end_date)).where(Membership.socio_id == socio.id)
    )
    inicio = max(hoy, ultimo_fin + timedelta(days=1)) if ultimo_fin else hoy
    fin = _sumar_meses(inicio, plan.duration_months) - timedelta(days=1)
 
    membresia = Membership(
        socio_id=socio.id,
        plan_id=plan.id,
        start_date=inicio,
        end_date=fin,
        price_paid=plan.final_price,
    )
    db.add(membresia)
    db.commit()
    db.refresh(membresia)
    return MembershipResponse.build(membresia)
 
 
@router.get("/{socio_id}/membresias", response_model=List[MembershipResponse])
def historial_membresias(
    socio_id: int = Path(le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """Membresías del socio, de la que termina más tarde a la más antigua."""
    socio = obtener_socio(db, socio_id, gym.id)
    membresias = db.scalars(
        select(Membership)
        .options(joinedload(Membership.plan))
        .where(Membership.socio_id == socio.id)
        .order_by(Membership.end_date.desc(), Membership.id.desc())
    ).all()
    return [MembershipResponse.build(m) for m in membresias]