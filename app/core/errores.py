"""Mensajes de validación en español y por campo (SCRUM-14 CA1)."""

from fastapi import Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Solo estas rutas usan el formato nuevo; el resto de la API conserva la
# respuesta 422 estándar de FastAPI para no cambiar el comportamiento existente.
RUTAS_CON_ERRORES_POR_CAMPO = ("/api/v1/socios",)

_MENSAJES = {
    "missing": "Este campo es obligatorio",
    "string_too_short": "Este campo es obligatorio",
    "string_too_long": "Máximo {max_length} caracteres",
    "date_parsing": "Fecha inválida",
    "date_from_datetime_parsing": "Fecha inválida",
    "date_past": "La fecha debe ser anterior a hoy",
}


async def responder_errores_por_campo(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Responde {"detail": "Datos inválidos", "errores": {campo: mensaje}}."""
    if not request.url.path.startswith(RUTAS_CON_ERRORES_POR_CAMPO):
        return await request_validation_exception_handler(request, error)

    errores: dict[str, str] = {}
    for detalle in error.errors():
        ubicacion = detalle["loc"][1:] or detalle["loc"]
        campo = ".".join(str(parte) for parte in ubicacion)
        plantilla = _MENSAJES.get(detalle["type"])
        if plantilla:
            mensaje = plantilla.format(**detalle.get("ctx", {}))
        elif detalle["type"].endswith("_invalido"):
            mensaje = detalle["msg"]
        else:
            mensaje = "Valor inválido"
        errores.setdefault(campo, mensaje)
    return JSONResponse(
        status_code=422, content={"detail": "Datos inválidos", "errores": errores}
    )
