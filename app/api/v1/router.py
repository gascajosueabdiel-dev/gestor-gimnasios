"""Enrutador principal de la versión 1 de la API."""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, gyms, socios, users, plans, attendance, cobros


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(gyms.router, prefix="/gyms", tags=["Gimnasios"])
api_router.include_router(users.router, prefix="/users", tags=["Usuarios"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Asistencias"])
api_router.include_router(plans.router, prefix="/gyms", tags=["Planes de Membresía"])
api_router.include_router(socios.router, prefix="/socios", tags=["Socios"])
api_router.include_router(cobros.router, prefix="/socios", tags=["Cobros"])
