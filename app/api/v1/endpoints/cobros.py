"""Endpoints para cobrar membresías con vencimiento automático."""


from datetime import date, datetime
from decimal import Decimal 
from typing import List 


from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session 


from app.api.deps import get_active_gym, get_current_user, get_db
from app.api.v1.endpoints.socios import  MAX_ID, obtener_socio
from app.core.fechas import calcular_vencimiento
from app.models.gym  import  Gym 
from app.models.membership_plan import MembershipPlan
from app.models.pago_membresia import PagoMembresia 
from app.models.socio_plan import Membership
from app.models.user import User 
from app.schemas.pago_membresia import CobroCreate, CobroResponse

router = APIRouter()

def _recibo(pago: PagoMembresia, membresia: Membership)  -> CobroResponse:
    """Arma la respuesta del cobro con el desglose  y las fecha"""
    return CobroResponse(
        id=pago.id,
        socio_id=pago.socio_id,
        membership_id=pago.membership_id,
        usuario_id=pago.usuario_id,
        plan_title=membresia.plan.title,
        monto_plan=float(pago.monto_plan),
        monto_inscripcion=float(pago.monto_inscripcion),
        monto=float(pago.monto),
        metodo_pago=pago.metodo_pago,
        fecha_pago=pago.fecha_pago,
        fecha_inicio=membresia.start_date,
        fecha_vencimiento=pago.fecha_vencimiento,
    )



@router.post(
    "/{socio_id}/cobros",
    response_model=CobroResponse,
    status_code=status.HTTP_201_CREATED,
)

def cobrar_membresia(
      request: CobroCreate,
      socio_id: int = Path(le=MAX_ID),
      db: Session = Depends(get_db),
      gym: Gym = Depends(get_active_gym),
      current_user: User = Depends(get_current_user),
):

    """
    Cobra un plan a un socio del gimnasio activo."""


    socio = obtener_socio(db, socio_id, gym.id)


    plan = db.scalar(
        select(MembershipPlan).where(
            MembershipPlan.id == request.plan_id,
            MembershipPlan.gym_id == gym.id,
            MembershipPlan.is_active.is_(True),
        )
    )

    if not plan: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= "Plan no encontrado en este gimnasio",
        )


    # Inscripcion: solo  si el socio nunca ha pagado antes 
    pago_previos = db.scalar(
        select(func.count(PagoMembresia.id)).where(PagoMembresia.socio_id == socio.id)
    )

    monto_inscripcion = (
        Decimal(str(gym.base_enrollment_fee)) if pago_previos == 0 else Decimal("0") 
    )

    monto_plan = plan.final_price
    monto_total = monto_plan + monto_inscripcion


    # fechas: empieza hoy o cuando venza la membresia vigente 

    hoy = date.today()
    ultimo_vencimiento = db.scalar(
        select(func.max(Membership.end_date)).where(Membership.socio_id == socio.id)
    )
    inicio = max(hoy, ultimo_vencimiento) if ultimo_vencimiento else hoy
    vencimiento = calcular_vencimiento(inicio, plan.duration_months)


    membresia = Membership(
        socio_id=socio.id,
        plan_id=plan.id,
        start_date=inicio,
        end_date=vencimiento,
        price_paid=monto_plan,
    )

    db.add(membresia)
    db.flush()  

    pago = PagoMembresia(
        socio_id=socio.id,
        membership_id=membresia.id, 
        usuario_id= current_user.id,
        monto_plan=monto_plan,
        monto_inscripcion=monto_inscripcion,
        monto=monto_total,
        metodo_pago=request.metodo_pago,
        fecha_pago=datetime.now(),
        fecha_vencimiento=vencimiento,
    )

    db.add(pago)
    db.commit()
    db.refresh(pago)
    db.refresh(membresia)
    return _recibo(pago, membresia)


@router.get("/{socio_id}/cobros", response_model=List[CobroResponse])
def historial_cobros(
    socio_id: int = Path(le=MAX_ID),
    db: Session = Depends(get_db),
    gym: Gym = Depends(get_active_gym),
):
    """Pagos del socio, del más reciente al más antiguo."""
    socio = obtener_socio(db, socio_id, gym.id)
    filas = db.execute(
        select(PagoMembresia, Membership)
        .join(Membership, PagoMembresia.membership_id == Membership.id)
        .where(PagoMembresia.socio_id == socio.id)
        .order_by(PagoMembresia.id.desc())
    ).all()
    return [_recibo(pago, membresia) for pago, membresia in filas]


  
