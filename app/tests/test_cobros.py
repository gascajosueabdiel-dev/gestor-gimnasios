"""Suite QA para cobrar membresías con vencimiento automático (SCRUM-17 / GYM-06)."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.fechas import calcular_vencimiento
from app.core.security import create_access_token
from app.models.gym import Gym
from app.models.membership_plan import MembershipPlan
from app.models.pago_membresia import PagoMembresia
from app.models.socio import Socio

COBROS_URL = "/api/v1/socios/{socio_id}/cobros"


# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------

def auth_headers(user_id: int, role: str, gym_ids: list[int]) -> dict:
    token = create_access_token(
        data={"sub": str(user_id), "user_id": user_id, "role": role, "gym_ids": gym_ids}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers():
    """Encargado (ID 2) del gimnasio 1; la inscripción base del gimnasio 1 es $50."""
    return auth_headers(2, "MANAGER", [1])


@pytest.fixture
def socio(db_session):
    s = Socio(gym_id=1, num_referencia_unico=1, nombre="Ana Pérez", celular="4421234567")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def plan_mensual(db_session):
    """$500 con 10 % de descuento = $450, 1 mes."""
    p = MembershipPlan(
        gym_id=1, title="Mensual", cost=Decimal("500"), duration_months=1,
        discount_percent=Decimal("10"),
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def otro_gym(db_session):
    gym = Gym(id=2, name="Gym Norte", base_enrollment_fee=0)
    db_session.add(gym)
    db_session.commit()
    return gym


def cobrar(client, headers, socio_id, plan_id, metodo="EFECTIVO"):
    return client.post(
        COBROS_URL.format(socio_id=socio_id),
        json={"plan_id": plan_id, "metodo_pago": metodo},
        headers=headers,
    )


@pytest.fixture
def hoy_es(monkeypatch):
    """Fija la fecha de 'hoy' que usa el endpoint de cobro."""

    def fijar(anio, mes, dia):
        class FechaFija(date):
            @classmethod
            def today(cls):
                return cls(anio, mes, dia)

        monkeypatch.setattr("app.api.v1.endpoints.cobros.date", FechaFija)

    return fijar


# ---------------------------------------------------------------------------
# Algoritmo de vencimiento (pruebas unitarias)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "inicio, meses, esperado",
    [
        (date(2027, 1, 31), 1, date(2027, 2, 28)),   # ejemplo del documento
        (date(2028, 1, 31), 1, date(2028, 2, 29)),   # año bisiesto
        (date(2027, 3, 31), 1, date(2027, 4, 30)),   # mes de 30 días
        (date(2027, 1, 30), 1, date(2027, 2, 28)),   # 30 de enero tampoco existe en febrero
        (date(2027, 1, 15), 1, date(2027, 2, 15)),   # caso normal
        (date(2026, 12, 15), 1, date(2027, 1, 15)),  # cambio de año
        (date(2026, 11, 30), 3, date(2027, 2, 28)),  # varios meses cruzando de año
        (date(2027, 8, 31), 6, date(2028, 2, 29)),   # 6 meses hacia febrero bisiesto
        (date(2028, 2, 29), 12, date(2029, 2, 28)),  # de bisiesto a no bisiesto
        (date(2027, 1, 31), 12, date(2028, 1, 31)),  # un año completo
    ],
)
def test_calcular_vencimiento_casos_limite(inicio, meses, esperado):
    assert calcular_vencimiento(inicio, meses) == esperado


@pytest.mark.parametrize("meses", [0, -1])
def test_calcular_vencimiento_rechaza_duracion_invalida(meses):
    with pytest.raises(ValueError):
        calcular_vencimiento(date(2027, 1, 1), meses)


# ---------------------------------------------------------------------------
# Inscripción: primera vez vs. pagos siguientes
# ---------------------------------------------------------------------------

def test_primer_pago_cobra_inscripcion(client, manager_headers, socio, plan_mensual):
    """Primer pago: plan $450 + inscripción base $50 = $500."""
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id)

    assert r.status_code == 201
    data = r.json()
    assert data["monto_plan"] == 450.0
    assert data["monto_inscripcion"] == 50.0
    assert data["monto"] == 500.0


def test_segundo_pago_no_cobra_inscripcion(client, manager_headers, socio, plan_mensual):
    """Pagos siguientes: solo el plan, sin inscripción."""
    cobrar(client, manager_headers, socio.id, plan_mensual.id)
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id, "TARJETA")

    assert r.status_code == 201
    data = r.json()
    assert data["monto_inscripcion"] == 0.0
    assert data["monto"] == 450.0


def test_inscripcion_es_por_socio(client, manager_headers, db_session, socio, plan_mensual):
    """Que un socio ya haya pagado no quita la inscripción a otro socio nuevo."""
    cobrar(client, manager_headers, socio.id, plan_mensual.id)
    otro = Socio(gym_id=1, num_referencia_unico=2, nombre="Luis", celular="4429876543")
    db_session.add(otro)
    db_session.commit()

    r = cobrar(client, manager_headers, otro.id, plan_mensual.id)
    assert r.json()["monto_inscripcion"] == 50.0


# ---------------------------------------------------------------------------
# Cálculo estricto del monto y datos del pago
# ---------------------------------------------------------------------------

def test_monto_lo_calcula_el_servidor(client, manager_headers, socio, plan_mensual):
    """Aunque el cliente mande un monto, se ignora y se cobra el precio del plan."""
    r = client.post(
        COBROS_URL.format(socio_id=socio.id),
        json={"plan_id": plan_mensual.id, "metodo_pago": "EFECTIVO", "monto": 1},
        headers=manager_headers,
    )
    assert r.status_code == 201
    assert r.json()["monto"] == 500.0


def test_guarda_pago_con_metodo_usuario_y_fechas(client, manager_headers, db_session, socio, plan_mensual):
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id, "TRANSFERENCIA")

    pago = db_session.get(PagoMembresia, r.json()["id"])
    assert pago.metodo_pago.value == "TRANSFERENCIA"
    assert pago.usuario_id == 2          # el encargado que cobró
    assert pago.socio_id == socio.id
    assert pago.fecha_pago is not None
    assert pago.fecha_vencimiento == date.fromisoformat(r.json()["fecha_vencimiento"])


@pytest.mark.parametrize("metodo", ["EFECTIVO", "TARJETA", "TRANSFERENCIA"])
def test_metodos_de_pago_validos(client, manager_headers, socio, plan_mensual, metodo):
    assert cobrar(client, manager_headers, socio.id, plan_mensual.id, metodo).status_code == 201


@pytest.mark.parametrize("metodo", ["BITCOIN", "efectivo", ""])
def test_metodo_de_pago_invalido_422(client, manager_headers, socio, plan_mensual, metodo):
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id, metodo)
    assert r.status_code == 422
    assert "metodo_pago" in r.json()["errores"]


# ---------------------------------------------------------------------------
# Fechas de vencimiento en el cobro
# ---------------------------------------------------------------------------

def test_cobro_el_31_de_enero_vence_28_de_febrero(client, manager_headers, socio, plan_mensual, hoy_es):
    """Caso límite del documento: cobro el 31/01 vence el 28/02."""
    hoy_es(2027, 1, 31)
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id)

    assert r.json()["fecha_inicio"] == "2027-01-31"
    assert r.json()["fecha_vencimiento"] == "2027-02-28"


def test_cobro_el_31_de_enero_en_bisiesto_vence_29_de_febrero(client, manager_headers, socio, plan_mensual, hoy_es):
    hoy_es(2028, 1, 31)
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id)
    assert r.json()["fecha_vencimiento"] == "2028-02-29"


def test_renovacion_anticipada_empieza_al_vencer_la_vigente(client, manager_headers, socio, plan_mensual, hoy_es):
    """Si paga antes de que venza, no pierde días: la nueva empieza cuando vence la actual."""
    hoy_es(2027, 1, 15)
    cobrar(client, manager_headers, socio.id, plan_mensual.id)       # 15/01 -> 15/02
    hoy_es(2027, 2, 10)
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id)   # pagó antes de vencer

    assert r.json()["fecha_inicio"] == "2027-02-15"
    assert r.json()["fecha_vencimiento"] == "2027-03-15"


def test_si_ya_vencio_la_nueva_empieza_hoy(client, manager_headers, socio, plan_mensual, hoy_es):
    hoy_es(2027, 1, 15)
    cobrar(client, manager_headers, socio.id, plan_mensual.id)       # vence 15/02
    hoy_es(2027, 4, 1)
    r = cobrar(client, manager_headers, socio.id, plan_mensual.id)

    assert r.json()["fecha_inicio"] == "2027-04-01"
    assert r.json()["fecha_vencimiento"] == "2027-05-01"


# ---------------------------------------------------------------------------
# Aislamiento por gimnasio y seguridad
# ---------------------------------------------------------------------------

def test_plan_de_otro_gimnasio_404(client, manager_headers, db_session, socio, otro_gym):
    plan_ajeno = MembershipPlan(gym_id=2, title="Ajeno", cost=Decimal("100"), duration_months=1)
    db_session.add(plan_ajeno)
    db_session.commit()

    r = cobrar(client, manager_headers, socio.id, plan_ajeno.id)
    assert r.status_code == 404
    assert r.json()["detail"] == "Plan no encontrado en este gimnasio"


def test_socio_de_otro_gimnasio_404(client, manager_headers, db_session, plan_mensual, otro_gym):
    socio_ajeno = Socio(gym_id=2, num_referencia_unico=1, nombre="Ajeno", celular="4420000000")
    db_session.add(socio_ajeno)
    db_session.commit()

    r = cobrar(client, manager_headers, socio_ajeno.id, plan_mensual.id)
    assert r.status_code == 404


def test_cobro_sin_token_401(client, socio, plan_mensual):
    r = client.post(
        COBROS_URL.format(socio_id=socio.id),
        json={"plan_id": plan_mensual.id, "metodo_pago": "EFECTIVO"},
    )
    assert r.status_code == 401


def test_no_se_guarda_nada_si_el_plan_no_existe(client, manager_headers, db_session, socio):
    r = cobrar(client, manager_headers, socio.id, 999)
    assert r.status_code == 404
    assert db_session.query(PagoMembresia).count() == 0


# ---------------------------------------------------------------------------
# Historial de pagos
# ---------------------------------------------------------------------------

def test_historial_del_mas_reciente_al_mas_antiguo(client, manager_headers, socio, plan_mensual):
    cobrar(client, manager_headers, socio.id, plan_mensual.id, "EFECTIVO")
    cobrar(client, manager_headers, socio.id, plan_mensual.id, "TARJETA")

    r = client.get(COBROS_URL.format(socio_id=socio.id), headers=manager_headers)
    assert r.status_code == 200
    assert [p["metodo_pago"] for p in r.json()] == ["TARJETA", "EFECTIVO"]
    assert [p["monto_inscripcion"] for p in r.json()] == [0.0, 50.0]
