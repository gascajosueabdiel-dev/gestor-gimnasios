def test_register_admin_success(client):
    """
    Prueba de CA1, CA2 y CA4: Registro exitoso de admin y gimnasio.
    """
    payload = {
        "email": "nuevo_admin@gym.com",
        "password": "SecurePassword123",
        "gym_name": "Power Gym Central",
        "location": "Calle Principal 123",
        "logo_url": "https://gym.com/logo.png",
        "base_enrollment_fee": 49.99,
    }
    response = client.post("/api/v1/auth/register-admin", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo_admin@gym.com"
    assert data["role"] == "ADMIN"
    assert data["gym"]["name"] == "Power Gym Central"
    assert "password" not in data  # CA4: No devuelve la contraseña


def test_register_admin_duplicate_email(client):
    """
    Prueba de CA3: El correo ya existe (HTTP 409 Conflict).
    """
    payload = {
        "email": "admin@test.com",  # Ya sembrado en conftest.py
        "password": "password123",
        "gym_name": "Gimnasio Duplicado",
        "base_enrollment_fee": 20.00,
    }
    response = client.post("/api/v1/auth/register-admin", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "El correo ya está registrado"


def test_register_admin_invalid_fee(client):
    """
    Prueba de CA2: Monto inválido con más de 2 decimales.
    """
    payload = {
        "email": "monto_invalido@gym.com",
        "password": "password123",
        "gym_name": "Gym Fee Error",
        "base_enrollment_fee": 50.123,
    }
    response = client.post("/api/v1/auth/register-admin", json=payload)
    assert response.status_code == 422  # Error de validación de Pydantic