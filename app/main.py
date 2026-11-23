"""Punto de entrada principal de la aplicación FastAPI."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import app.models
from app.api.v1.router import api_router
from app.core.errores import responder_errores_por_campo
from app.db.base import Base
from app.db.session import engine

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"  # app/static

# Creación automática de las tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gimnasios",
    description="Sistema de gestión de gimnasios con RBAC y multisede",
    version="1.0.0",
)

# Errores de validación en español y por campo (SCRUM-14)
app.add_exception_handler(RequestValidationError, responder_errores_por_campo)

# Enrutador de la API v1
app.include_router(api_router, prefix="/api/v1")

# Montaje de la interfaz frontend estática
# Se hizo un cambio para evitar que el inicio dependiera de una ruta relativa 
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")