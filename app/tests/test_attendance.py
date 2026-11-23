"""Pruebas de asistencias (CA1 a CA4).

TODO: ajustar a los fixtures reales de tu conftest.py. Aquí se asume:
- client: TestClient de FastAPI
- db: Session de pruebas (la misma BD que usa la app durante el test)
- gym: Gym del encargado
- otro_gym: un Gym distinto, al que el encargado NO pertenece
- manager_headers: headers con el JWT de un MANAGER cuyo gimnasio activo es `gym`
Los helpers de abajo se repiten en test_membresias.py; conviene moverlos al conftest.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models.attendance import Attendance
from app.models.socio_plan import Membership
from app.models.membership_plan import MembershipPlan
from app.models.socio import Socio

URL = "/api/v1/attendance"


def crear_socio(db, gym, num, nombre="Ana Pérez"):
    socio = Socio(
        gym_id=gym.id,
        num_referencia_unico=num,
        nombre=nombre,
        celular="4421234567",
    )
    db.add(socio)
    db.commit()
    db.refresh(socio)
    return socio


def crear_membresia(db, socio, inicio, fin):
    """Crea un plan y una membresía del socio con el periodo indicado."""
    plan = MembershipPlan(
        gym_id=socio.gym_id,
        title="Mensual",
        cost=Decimal("500.00"),
        duration_months=1,
        discount_percent=Decimal("0"),
    )
    db.add(plan)
    db.flush()
    membresia = Membership(
        socio_id=socio.id,
        plan_id=plan.id,
        start_date=inicio,
        end_date=fin,
        price_paid=plan.final_price,
    )
    db.add(membresia)
    db.commit()
    return membresia


def total_asistencias(db) -> int:
    return db.scalar(select(func.count()).select_from(Attendance))


# ---------- CA1: registro de un socio con membresía activa ----------

def test_registra_asistencia_de_socio_activo(client, db, gym, manager_headers):
    hoy = date.today()
    socio = crear_socio(db, gym, 101)
    crear_membresia(db, socio, hoy - timedelta(days=5), hoy + timedelta(days=25))

    r = client.post(URL, json={"num_referencia": 101}, headers=manager_headers)

    assert r.status_code == 201
    body = r.json()
    assert body["socio_nombre"] == "Ana Pérez"
    assert body["member_id"] == socio.id
    assert body["gym_id"] == gym.id
    assert body["date_time"]  # fecha y hora puestas por la BD
    assert total_asistencias(db) == 1


def test_membresia_que_vence_hoy_todavia_deja_entrar(client, db, gym, manager_headers):
    hoy = date.today()
    socio = crear_socio(db, gym, 102)
    crear_membresia(db, socio, hoy - timedelta(days=30), hoy)

    r = client.post(URL, json={"num_referencia": 102}, headers=manager_headers)

    assert r.status_code == 201


# ---------- CA3: socio inexistente ----------

def test_socio_inexistente_no_guarda_registro(client, db, gym, manager_headers):
    r = client.post(URL, json={"num_referencia": 999}, headers=manager_headers)

    assert r.status_code == 404
    assert r.json()["detail"] == "Socio no encontrado"
    assert total_asistencias(db) == 0


def test_socio_de_otro_gimnasio_se_trata_como_inexistente(
    client, db, gym, otro_gym, manager_headers
):
    hoy = date.today()
    ajeno = crear_socio(db, otro_gym, 202)
    crear_membresia(db, ajeno, hoy - timedelta(days=5), hoy + timedelta(days=25))

    r = client.post(URL, json={"num_referencia": 202}, headers=manager_headers)

    assert r.status_code == 404
    assert r.json()["detail"] == "Socio no encontrado"
    assert total_asistencias(db) == 0


# ---------- CA2: alerta por membresía vencida ----------

def test_membresia_vencida_avisa_y_no_guarda_hasta_que_el_encargado_decide(
    client, db, gym, manager_headers
):
    hoy = date.today()
    socio = crear_socio(db, gym, 303, nombre="Luis Gómez")
    crear_membresia(db, socio, hoy - timedelta(days=40), hoy - timedelta(days=10))

    # 1er intento: alerta, sin registro
    r = client.post(URL, json={"num_referencia": 303}, headers=manager_headers)
    assert r.status_code == 409
    detalle = r.json()["detail"]
    assert detalle["codigo"] == "MEMBRESIA_VENCIDA"
    assert detalle["mensaje"] == "Membresía vencida"
    assert detalle["socio_nombre"] == "Luis Gómez"
    assert total_asistencias(db) == 0

    # El Encargado permite la entrada: ahora sí se guarda
    r = client.post(
        URL,
        json={"num_referencia": 303, "permitir_membresia_vencida": True},
        headers=manager_headers,
    )
    assert r.status_code == 201
    assert total_asistencias(db) == 1


def test_socio_sin_ninguna_membresia_tambien_dispara_la_alerta(
    client, db, gym, manager_headers
):
    crear_socio(db, gym, 304)

    r = client.post(URL, json={"num_referencia": 304}, headers=manager_headers)

    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "MEMBRESIA_VENCIDA"
    assert total_asistencias(db) == 0


# ---------- CA4: historial ordenado ----------

def test_historial_de_la_mas_reciente_a_la_mas_antigua(client, db, gym, manager_headers):
    from datetime import datetime, timezone

    socio = crear_socio(db, gym, 404)
    # Se insertan desordenadas a propósito
    fechas = [
        datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc),
    ]
    creadas = [Attendance(member_id=socio.id, gym_id=gym.id, date_time=f) for f in fechas]
    db.add_all(creadas)
    db.commit()
    medio, reciente, antigua = creadas

    r = client.get(f"/api/v1/socios/{socio.id}/asistencias", headers=manager_headers)

    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [reciente.id, medio.id, antigua.id]


def test_historial_de_socio_de_otro_gimnasio_da_404(
    client, db, otro_gym, manager_headers
):
    ajeno = crear_socio(db, otro_gym, 505)

    r = client.get(f"/api/v1/socios/{ajeno.id}/asistencias", headers=manager_headers)

    assert r.status_code == 404