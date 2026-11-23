"""Suite QA para Administración de Planes de Membresía (SCRUM-16 / SCRUM-52)."""

import pytest
from app.core.security import create_access_token
from app.models.gym import Gym
from app.models.membership_plan import MembershipPlan

PLANS_URL = "/api/v1/gyms/{gym_id}/plans"


def auth_headers(user_id: int, role: str, gym_ids: list[int]) -> dict:
    """Genera el encabezado Authorization con un JWT válido."""
    token = create_access_token(
        data={"sub": str(user_id), "user_id": user_id, "role": role, "gym_ids": gym_ids}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return auth_headers(1, "ADMIN", [1])


@pytest.fixture
def manager_headers():
    return auth_headers(2, "MANAGER", [1])


@pytest.fixture
def valid_plan():
    return {
        "title": "Plan Trimestral",
        "description": "Acceso total por 3 meses",
        "cost": 1500.00,
        "duration_months": 3,
        "discount_percent": 10,
    }


@pytest.fixture
def existing_plan(db_session):
    """Plan ya guardado en el gimnasio 1."""
    plan = MembershipPlan(
        gym_id=1, title="Plan Mensual", cost=500, duration_months=1, discount_percent=0
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def second_gym(db_session):
    """Gimnasio 2 con un plan propio; el Encargado de prueba NO está asignado."""
    gym = Gym(id=2, name="Gym Norte", base_enrollment_fee=0)
    db_session.add(gym)
    db_session.flush()
    db_session.add(
        MembershipPlan(gym_id=2, title="Plan Norte", cost=800, duration_months=2)
    )
    db_session.commit()
    return gym


# ---------------------------------------------------------------------------
# Creación exitosa y CA2 (precio final calculado)
# ---------------------------------------------------------------------------

def test_admin_creates_plan_with_final_price(client, admin_headers, valid_plan):
    """CA2: El admin crea un plan y el sistema devuelve el precio final calculado."""
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=admin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["gym_id"] == 1
    assert data["title"] == "Plan Trimestral"
    assert data["cost"] == 1500.00
    assert data["discount_percent"] == 10
    assert data["final_price"] == 1350.00


@pytest.mark.parametrize(
    "cost, discount, expected",
    [
        (1000, 0, 1000.00),
        (1000, 100, 0.00),
        (999.99, 15, 849.99),
        (333.33, 33.33, 222.23),
    ],
)
def test_final_price_calculation(client, admin_headers, valid_plan, cost, discount, expected):
    """CA2: Precio final = costo - costo * descuento / 100, redondeado a 2 decimales."""
    valid_plan.update(cost=cost, discount_percent=discount)
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=admin_headers
    )

    assert response.status_code == 201
    assert response.json()["final_price"] == expected


def test_discount_defaults_to_zero(client, admin_headers, valid_plan):
    """CA2: Si no se envía descuento, se asume 0 y el precio final es igual al costo."""
    del valid_plan["discount_percent"]
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=admin_headers
    )

    assert response.status_code == 201
    assert response.json()["final_price"] == valid_plan["cost"]


# ---------------------------------------------------------------------------
# CA1 y CA2: Validaciones (HTTP 422 con mensaje de error)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "field, value, message",
    [
        ("title", "", "El título es obligatorio"),
        ("title", "   ", "El título es obligatorio"),
        ("title", None, "El título es obligatorio"),
        ("cost", 0, "El costo debe ser mayor a 0"),
        ("cost", -100, "El costo debe ser mayor a 0"),
        ("cost", 10.555, "El costo admite máximo 2 decimales"),
        ("duration_months", 0, "La duración debe ser un número entero de 1 a 12 meses"),
        ("duration_months", 13, "La duración debe ser un número entero de 1 a 12 meses"),
        ("duration_months", 1.5, "La duración debe ser un número entero de 1 a 12 meses"),
        ("discount_percent", -1, "El descuento debe ser un porcentaje entre 0 y 100"),
        ("discount_percent", 100.01, "El descuento debe ser un porcentaje entre 0 y 100"),
    ],
)
def test_invalid_plan_returns_422(client, admin_headers, valid_plan, field, value, message):
    """CA1/CA2: Datos inválidos se rechazan con 422 y un mensaje de error claro."""
    valid_plan[field] = value
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=admin_headers
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(message in error["msg"] for error in errors)


def test_missing_required_fields_returns_422(client, admin_headers):
    """CA1: Sin título, costo ni duración el plan no se crea."""
    response = client.post(PLANS_URL.format(gym_id=1), json={}, headers=admin_headers)

    assert response.status_code == 422
    missing = {error["loc"][-1] for error in response.json()["detail"]}
    assert {"title", "cost", "duration_months"} <= missing


@pytest.mark.parametrize("duration", [1, 12])
def test_duration_limits_are_valid(client, admin_headers, valid_plan, duration):
    """CA1: 1 y 12 meses son valores válidos (límites incluidos)."""
    valid_plan["duration_months"] = duration
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=admin_headers
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# CA3: Restricción de rol (403 para Encargado)
# ---------------------------------------------------------------------------

def test_manager_cannot_create_plan_403(client, manager_headers, valid_plan, db_session):
    """CA3: Un Encargado que intenta crear un plan recibe 403 y no se guarda nada."""
    response = client.post(
        PLANS_URL.format(gym_id=1), json=valid_plan, headers=manager_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene permisos para realizar esta acción"
    assert db_session.query(MembershipPlan).count() == 0


def test_manager_cannot_update_plan_403(client, manager_headers, valid_plan, existing_plan, db_session):
    """CA3: Un Encargado que intenta modificar un plan recibe 403 y el plan no cambia."""
    response = client.put(
        f"{PLANS_URL.format(gym_id=1)}/{existing_plan.id}",
        json=valid_plan,
        headers=manager_headers,
    )

    assert response.status_code == 403
    db_session.refresh(existing_plan)
    assert existing_plan.title == "Plan Mensual"


def test_manager_can_list_plans_of_assigned_gym(client, manager_headers, existing_plan):
    """CA3/CA4: El Encargado sí puede consultar los planes de su gimnasio."""
    response = client.get(PLANS_URL.format(gym_id=1), headers=manager_headers)

    assert response.status_code == 200
    assert [plan["title"] for plan in response.json()] == ["Plan Mensual"]


def test_plans_require_token_401(client):
    """Sin token no se puede listar planes."""
    response = client.get(PLANS_URL.format(gym_id=1))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Edición exitosa
# ---------------------------------------------------------------------------

def test_admin_updates_plan(client, admin_headers, valid_plan, existing_plan):
    """El admin edita un plan y se recalcula el precio final."""
    valid_plan.update(title="Plan Mensual Promo", cost=500, discount_percent=20)
    response = client.put(
        f"{PLANS_URL.format(gym_id=1)}/{existing_plan.id}",
        json=valid_plan,
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Plan Mensual Promo"
    assert data["final_price"] == 400.00


def test_update_with_invalid_data_returns_422(client, admin_headers, valid_plan, existing_plan):
    """CA1: Al editar también se validan los datos."""
    valid_plan["cost"] = 0
    response = client.put(
        f"{PLANS_URL.format(gym_id=1)}/{existing_plan.id}",
        json=valid_plan,
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_update_nonexistent_plan_404(client, admin_headers, valid_plan):
    """Editar un plan que no existe responde 404."""
    response = client.put(
        f"{PLANS_URL.format(gym_id=1)}/999", json=valid_plan, headers=admin_headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# CA4: Los planes pertenecen a un gimnasio y solo se listan los del gimnasio activo
# ---------------------------------------------------------------------------

def test_list_only_returns_plans_of_selected_gym(client, admin_headers, existing_plan, second_gym):
    """CA4: Cada gimnasio solo lista sus propios planes."""
    gym1 = client.get(PLANS_URL.format(gym_id=1), headers=admin_headers).json()
    gym2 = client.get(PLANS_URL.format(gym_id=2), headers=admin_headers).json()

    assert [plan["title"] for plan in gym1] == ["Plan Mensual"]
    assert [plan["title"] for plan in gym2] == ["Plan Norte"]
    assert all(plan["gym_id"] == 1 for plan in gym1)


def test_manager_cannot_list_unassigned_gym_403(client, manager_headers, second_gym):
    """CA4: El Encargado no ve planes de un gimnasio que no tiene asignado."""
    response = client.get(PLANS_URL.format(gym_id=2), headers=manager_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene acceso asignado a este gimnasio"


def test_cannot_edit_plan_through_another_gym_404(client, admin_headers, valid_plan, existing_plan, second_gym):
    """CA4: Un plan del gimnasio 1 no puede editarse usando la ruta del gimnasio 2."""
    response = client.put(
        f"{PLANS_URL.format(gym_id=2)}/{existing_plan.id}",
        json=valid_plan,
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_inactive_gym_does_not_list_plans_404(client, admin_headers, existing_plan, db_session):
    """CA4: Si el gimnasio está inactivo no se listan sus planes."""
    gym = db_session.get(Gym, 1)
    gym.is_active = False
    db_session.commit()

    response = client.get(PLANS_URL.format(gym_id=1), headers=admin_headers)
    assert response.status_code == 404


def test_create_plan_in_nonexistent_gym_404(client, admin_headers, valid_plan):
    """CA4: No se puede crear un plan en un gimnasio que no existe."""
    response = client.post(
        PLANS_URL.format(gym_id=999), json=valid_plan, headers=admin_headers
    )
    assert response.status_code == 404
