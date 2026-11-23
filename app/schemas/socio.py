"""Schemas de Pydantic V2 para el registro y consulta de socios."""

import re
from datetime import date
from typing import Annotated, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    PastDate,
    StringConstraints,
)
from pydantic_core import PydanticCustomError


def _validar_celular(celular: str) -> str:
    """CA1: exactamente 10 dígitos numéricos.

    Se usa [0-9] y no \\d, porque \\d también acepta dígitos de otros alfabetos.
    """
    if not re.fullmatch(r"[0-9]{10}", celular):
        raise PydanticCustomError(
            "celular_invalido",
            "El celular debe tener exactamente 10 dígitos numéricos",
        )
    return celular


class SocioCreate(BaseModel):
    """Datos para registrar o actualizar un socio. El número lo asigna el sistema."""

    nombre: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    celular: Annotated[str, AfterValidator(_validar_celular)]
    fecha_nacimiento: Optional[PastDate] = None
    metas: Optional[
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
    ] = None


class SocioResponse(BaseModel):
    """Ficha del socio."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    num_referencia_unico: int
    nombre: str
    celular: str
    fecha_nacimiento: Optional[date] = None
    metas: Optional[str] = None


class GimnasioActivoRequest(BaseModel):
    """Gimnasio con el que el usuario quiere trabajar."""

    gym_id: int
