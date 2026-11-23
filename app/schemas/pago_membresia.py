

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.pago_membresia import MetodoPago

MAX_ID = 2_147_483_647


class CobroCreate(BaseModel):
  """Lo que manda la pantalla de cobro.""" 

  plan_id: int = Field(..., ge=1, le=MAX_ID)
  metodo_pago: MetodoPago



class CobroResponse(BaseModel):
    """Recibo del cobro con el desglose del monto y las fechas."""

    model_config = ConfigDict(from_attributes=True)


    id: int 
    socio_id: int 
    membership_id: int
    usuario_id: int
    plan_title: str
    monto_plan: float
    monto_inscripcion: float
    monto: float
    metodo_pago: MetodoPago
    fecha_pago: datetime
    fecha_inicio: date
    fecha_vencimiento: date

   
