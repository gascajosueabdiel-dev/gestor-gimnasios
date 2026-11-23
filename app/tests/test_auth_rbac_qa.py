"""Suite de Pruebas QA para Autenticación JWT y RBAC Multisede."""

from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings
from app.core.security import create_access_token


def test_login_success(client):
    """Escenario 1: Inicio de sesión exitoso con credenciales válidas (HTTP 200)."""
    payload = {"email": "admin@test.com", "password": "password123"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verificar claims requeridos en el payload JWT
    decoded = jwt.decode(
        data["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    assert decoded["role"] == "ADMIN"
    assert "user_id" in decoded
    assert "gym_ids" in decoded


def test_login_invalid_credentials(client):
    """Escenario 2: Credenciales inválidas (HTTP 401)."""
    payload = {"email": "admin@test.com", "password": "password_incorrecto"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contrasena incorrectos"


def test_protected_route_expired_token(client):
    """Escenario 3: Petición con token expirado (HTTP 401)."""
    expire = datetime.now(timezone.utc) - timedelta(minutes=10)
    payload = {
        "sub": "1",
        "user_id": 1,
        "role": "ADMIN",
        "gym_ids": [1],
        "exp": expire,
    }
    expired_token = jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/gyms/1", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido o expirado"


def test_protected_route_missing_token(client):
    """Escenario 3 (Variante): Petición sin token de autenticación (HTTP 401)."""
    response = client.get("/api/v1/gyms/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_manager_role_restriction_403(client):
    """Escenario 4: Encargado intentando crear otro usuario (HTTP 403)."""
    manager_token = create_access_token(
        data={"user_id": 2, "role": "MANAGER", "gym_ids": [1]}
    )
    headers = {"Authorization": f"Bearer {manager_token}"}

    payload = {
        "email": "nuevo.manager@gym.com",
        "password": "Password123",
        "gym_ids": [1],
    }

    response = client.post(
        "/api/v1/users/managers", json=payload, headers=headers
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "No tiene permisos para realizar esta acción"
    )


def test_manager_access_unassigned_gym_403(client):
    """Escenario 4 (Variante): Encargado accediendo a un gimnasio no asignado (HTTP 403)."""
    manager_token = create_access_token(
        data={"user_id": 2, "role": "MANAGER", "gym_ids": [1]}
    )
    headers = {"Authorization": f"Bearer {manager_token}"}

    response = client.get("/api/v1/gyms/99", headers=headers)

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "No tiene acceso asignado a este gimnasio"
    )