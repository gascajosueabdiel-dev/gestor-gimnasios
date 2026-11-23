from datetime import datetime
from typing import TYPE_CHECKING
 
from pydantic import BaseModel, Field
 
if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.socio import Socio
 
MAX_ID = 2_147_483_647
 
class AttendanceCreateRequest(BaseModel):
    """Entrada de Recepción: el número de referencia que dicta el socio (CA1)."""
 
    num_referencia: int = Field(..., ge=1, le=MAX_ID)
    # CA2: el Encargado decide. El primer intento va en False; si el sistema avisa
    # "Membresía vencida" y el Encargado acepta, el frontend repite con True.
    permitir_membresia_vencida: bool = False
 
 
class AttendanceResponse(BaseModel):
    """Salida de asistencias, con los datos del socio que Recepción necesita ver."""
 
    id: int
    member_id: int
    gym_id: int
    date_time: datetime
    socio_nombre: str
    num_referencia_unico: int
 
    @classmethod
    def build(cls, asistencia: "Attendance", socio: "Socio") -> "AttendanceResponse":
        """Arma la respuesta combinando la asistencia con los datos del socio."""
        return cls(
            id=asistencia.id,
            member_id=asistencia.member_id,
            gym_id=asistencia.gym_id,
            date_time=asistencia.date_time,
            socio_nombre=socio.nombre,
            num_referencia_unico=socio.num_referencia_unico,
        )