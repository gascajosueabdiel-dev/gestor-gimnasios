"""Pruebas de asignación de planes de membresía a socios.

Usa los mismos fixtures que test_attendance.py (client, db, gym, otro_gym,
manager_headers). TODO: mover los helpers al conftest para no duplicarlos.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.models.socio_plan import Membership
from app.models.membership_plan import MembershipPlan
from app.models.socio import Socio


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


def crear_plan(db, gym, costo="500.00", meses=3, descuento="0"):
    plan = MembershipPlan(
        gym_id=gym.id,
        title="Trimestral",
        cost=Decimal(costo),
        duration_months=meses,
        discount_percent=Decimal(descuento),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_asigna_plan_con_fechas_y_precio_calculados(client, db, gym, manager_headers):
    socio = crear_socio(db, gym, 101)
    plan = crear_plan(db, gym, costo="500.00", meses=3, descuento="10")

    r = client.post(
        f"/api/v1/socios/{socio.id}/membresias",
        json={"plan_id": plan.id},
        headers=manager_headers,
    )

    assert r.status_code == 201
    body = r.json()
    assert body["price_paid"] == 450.0  # 500 con 10 % de descuento
    assert body["start_date"] == date.today().isoformat()
    assert body["vigente"] is True
    dias = (date.fromisoformat(body["end_date"]) - date.fromisoformat(body["start_date"])).days
    assert 88 <= dias <= 91  # tres meses calendario, con el último día incluido


def test_plan_de_otro_gimnasio_da_404(client, db, gym, otro_gym, manager_headers):
    socio = crear_socio(db, gym, 102)
    plan_ajeno = crear_plan(db, otro_gym)

    r = client.post(
        f"/api/v1/socios/{socio.id}/membresias",
        json={"plan_id": plan_ajeno.id},
        headers=manager_headers,
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Plan no encontrado en este gimnasio"


def test_renovacion_anticipada_empieza_al_dia_siguiente_de_la_vigente(
    client, db, gym, manager_headers
):
    hoy = date.today()
    socio = crear_socio(db, gym, 103)
    plan = crear_plan(db, gym, meses=1)
    db.add(
        Membership(
            socio_id=socio.id,
            plan_id=plan.id,
            start_date=hoy - timedelta(days=20),
            end_date=hoy + timedelta(days=10),
            price_paid=plan.final_price,
        )
    )
    db.commit()

    r = client.post(
        f"/api/v1/socios/{socio.id}/membresias",
        json={"plan_id": plan.id},
        headers=manager_headers,
    )

    assert r.status_code == 201
    assert r.json()["start_date"] == (hoy + timedelta(days=11)).isoformat()