"""SCRUM-14: Registrar socio con número de referencia."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.gym import Gym
from app.models.socio import Socio
from app.models.user import User, UserRole

URL = "/api/v1/socios"
SOCIO = {"nombre": "Mariana López", "celular": "4421234567"}
CELULAR_INVALIDO = "El celular debe tener exactamente 10 dígitos numéricos"


@pytest.fixture
def gym_norte(db_session):
    """Gimnasio 2 con su propio Encargado (id 3). El de conftest solo tiene el 1."""
    norte = Gym(id=2, name="Sucursal Norte", base_enrollment_fee=0)
    encargado = User(
        id=3,
        email="norte@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
    )
    encargado.gyms.append(norte)
    db_session.add(encargado)
    db_session.commit()
    return norte


def cabeceras(client, email):
    respuesta = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def activar(client, auth, gym_id):
    respuesta = client.post(
        "/api/v1/auth/active-gym", json={"gym_id": gym_id}, headers=auth
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture
def auth_manager(client):
    return cabeceras(client, "manager@test.com")


@pytest.fixture
def auth_admin(client):
    return cabeceras(client, "admin@test.com")


@pytest.fixture
def auth_norte(client, gym_norte):
    return cabeceras(client, "norte@test.com")


def registrar(client, auth, **cambios):
    return client.post(URL, json={**SOCIO, **cambios}, headers=auth)


def nombres(respuesta):
    return [s["nombre"] for s in respuesta.json()]


# CA1: nombre y celular obligatorios, con error por campo ---------------------


def test_ca1_registra_socio_con_datos_minimos(client, auth_manager):
    respuesta = registrar(client, auth_manager)

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == SOCIO["nombre"]
    assert respuesta.json()["celular"] == SOCIO["celular"]


@pytest.mark.parametrize("campo", ["nombre", "celular"])
def test_ca1_campo_faltante_da_error_en_ese_campo(client, auth_manager, campo):
    cuerpo = {k: v for k, v in SOCIO.items() if k != campo}

    respuesta = client.post(URL, json=cuerpo, headers=auth_manager)

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"] == {campo: "Este campo es obligatorio"}


def test_ca1_nombre_acepta_exactamente_100_caracteres(client, auth_manager):
    assert registrar(client, auth_manager, nombre="a" * 100).status_code == 201


def test_ca1_nombre_de_101_caracteres_se_rechaza(client, auth_manager):
    respuesta = registrar(client, auth_manager, nombre="a" * 101)

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"] == {"nombre": "Máximo 100 caracteres"}


def test_ca1_nombre_solo_con_espacios_se_rechaza(client, auth_manager):
    respuesta = registrar(client, auth_manager, nombre="   ")

    assert respuesta.json()["errores"] == {"nombre": "Este campo es obligatorio"}


@pytest.mark.parametrize(
    "celular",
    ["442123456", "44212345678", "44212345ab", "442 123 45", "", "٠١٢٣٤٥٦٧٨٩"],
)
def test_ca1_celular_invalido_se_rechaza(client, auth_manager, celular):
    respuesta = registrar(client, auth_manager, celular=celular)

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"] == {"celular": CELULAR_INVALIDO}


def test_ca1_reporta_un_error_por_cada_campo(client, auth_manager):
    respuesta = registrar(client, auth_manager, nombre="", celular="1")

    assert set(respuesta.json()["errores"]) == {"nombre", "celular"}


@pytest.mark.parametrize(
    ("fecha", "mensaje"),
    [
        ("no-es-fecha", "Fecha inválida"),
        ("2999-01-01", "La fecha debe ser anterior a hoy"),
    ],
)
def test_ca1_fecha_de_nacimiento_invalida(client, auth_manager, fecha, mensaje):
    respuesta = registrar(client, auth_manager, fecha_nacimiento=fecha)

    assert respuesta.json()["errores"] == {"fecha_nacimiento": mensaje}


def test_ca1_otras_rutas_conservan_el_422_estandar(client):
    respuesta = client.post("/api/v1/auth/login", json={})

    assert respuesta.status_code == 422
    assert isinstance(respuesta.json()["detail"], list)


# CA2: número de referencia automático y único por gimnasio -------------------


def test_ca2_numero_automatico_e_incremental(client, auth_manager):
    numeros = [
        registrar(client, auth_manager).json()["num_referencia_unico"]
        for _ in range(3)
    ]

    assert numeros == [1, 2, 3]


def test_ca2_cliente_no_puede_elegir_el_numero(client, auth_manager):
    respuesta = registrar(client, auth_manager, num_referencia_unico=999)

    assert respuesta.json()["num_referencia_unico"] == 1


def test_ca2_numeracion_independiente_por_gimnasio(client, auth_manager, auth_norte):
    registrar(client, auth_manager)
    registrar(client, auth_manager)

    respuesta = registrar(client, auth_norte)

    assert respuesta.json()["num_referencia_unico"] == 1


def test_ca2_alta_rechazada_no_consume_numero(client, auth_manager):
    registrar(client, auth_manager, celular="1")

    assert registrar(client, auth_manager).json()["num_referencia_unico"] == 1


def test_ca2_la_base_impide_duplicados(client, auth_manager, db_session):
    registrar(client, auth_manager)

    db_session.add(
        Socio(gym_id=1, num_referencia_unico=1, nombre="Copia", celular="4420000000")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_ca2_actualizar_no_cambia_el_numero(client, auth_manager):
    socio = registrar(client, auth_manager).json()

    respuesta = client.put(
        f"{URL}/{socio['id']}",
        json={"nombre": "Otra", "celular": "4429999999", "num_referencia_unico": 77},
        headers=auth_manager,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Otra"
    assert respuesta.json()["num_referencia_unico"] == 1


# CA3: aislamiento por gimnasio activo ----------------------------------------


def test_ca3_socio_queda_en_el_gimnasio_activo(client, auth_manager, gym_norte):
    respuesta = registrar(client, auth_manager, gym_id=2)

    assert respuesta.json()["gym_id"] == 1


@pytest.mark.parametrize(("metodo", "cuerpo"), [("GET", None), ("PUT", SOCIO)])
def test_ca3_otro_gimnasio_recibe_404(
    client, auth_manager, auth_norte, metodo, cuerpo
):
    socio = registrar(client, auth_manager).json()

    respuesta = client.request(
        metodo, f"{URL}/{socio['id']}", json=cuerpo, headers=auth_norte
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Socio no encontrado"


def test_ca3_busqueda_no_incluye_otros_gimnasios(client, auth_manager, auth_norte):
    registrar(client, auth_manager, nombre="Propio")
    registrar(client, auth_norte, nombre="Ajeno")

    assert nombres(client.get(URL, headers=auth_manager)) == ["Propio"]
    respuesta = client.get(URL, params={"search": "Ajeno"}, headers=auth_manager)
    assert respuesta.json() == []


def test_ca3_admin_cambia_de_gimnasio_y_solo_ve_el_activo(
    client, auth_admin, gym_norte
):
    socio = registrar(client, auth_admin).json()
    auth_admin_norte = activar(client, auth_admin, 2)

    assert client.get(f"{URL}/{socio['id']}", headers=auth_admin_norte).status_code == 404
    assert registrar(client, auth_admin_norte).json()["gym_id"] == 2


def test_ca3_encargado_no_puede_activar_gimnasio_no_asignado(
    client, auth_manager, gym_norte
):
    respuesta = client.post(
        "/api/v1/auth/active-gym", json={"gym_id": 2}, headers=auth_manager
    )

    assert respuesta.status_code == 403


def test_ca3_activar_gimnasio_inexistente_responde_404(client, auth_admin):
    respuesta = client.post(
        "/api/v1/auth/active-gym", json={"gym_id": 999}, headers=auth_admin
    )

    assert respuesta.status_code == 404


def test_ca3_cambiar_de_gimnasio_no_alarga_la_sesion(client, gym_norte):
    def decodificar(auth):
        token = auth["Authorization"].removeprefix("Bearer ")
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # Sesión a la que le quedan 5 minutos: el token nuevo no debe durar 60.
    original = {
        "Authorization": "Bearer "
        + create_access_token(
            {"user_id": 1, "role": "ADMIN", "gym_ids": [1]},
            expires_delta=timedelta(minutes=5),
        )
    }

    nuevo = activar(client, original, 2)

    assert decodificar(nuevo)["exp"] == decodificar(original)["exp"]
    assert decodificar(nuevo)["active_gym_id"] == 2


def test_ca3_gimnasio_activo_retirado_responde_403(client, db_session, gym_norte):
    encargado = db_session.get(User, 2)
    encargado.gyms.append(gym_norte)
    db_session.commit()
    auth_norte = activar(client, cabeceras(client, "manager@test.com"), 2)

    encargado.gyms.remove(gym_norte)
    db_session.commit()

    assert client.get(URL, headers=auth_norte).status_code == 403


def test_ca3_retirar_la_asignacion_aplica_de_inmediato(
    client, auth_manager, db_session
):
    db_session.get(User, 2).gyms.clear()
    db_session.commit()

    assert client.get(URL, headers=auth_manager).status_code == 403


def test_ca3_sin_token_responde_401(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=SOCIO).status_code == 401


def test_ca3_token_expirado_responde_401(client):
    token = jwt.encode(
        {"user_id": 2, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    respuesta = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401


# CA4: búsqueda por nombre o número, y ficha ----------------------------------


@pytest.fixture
def socios(client, auth_manager):
    return [
        registrar(client, auth_manager, nombre=nombre).json()
        for nombre in ["Mariana López", "Mario Ruiz", "Ana Peña"]
    ]


def buscar(client, auth, termino):
    return client.get(URL, params={"search": termino}, headers=auth)


def test_ca4_busca_por_parte_del_nombre(client, auth_manager, socios):
    assert nombres(buscar(client, auth_manager, "MARI")) == [
        "Mariana López",
        "Mario Ruiz",
    ]


def test_ca4_busca_por_numero_de_referencia(client, auth_manager, socios):
    assert nombres(buscar(client, auth_manager, "3")) == ["Ana Peña"]


def test_ca4_numero_es_coincidencia_exacta(client, auth_manager, socios):
    assert buscar(client, auth_manager, "33").json() == []


def test_ca4_sin_resultados_devuelve_lista_vacia(client, auth_manager, socios):
    respuesta = buscar(client, auth_manager, "Zoe")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_ca4_sin_termino_lista_todos_ordenados(client, auth_manager, socios):
    assert nombres(client.get(URL, headers=auth_manager)) == [
        "Ana Peña",
        "Mariana López",
        "Mario Ruiz",
    ]


def test_ca4_comodines_se_buscan_literalmente(client, auth_manager, socios):
    assert buscar(client, auth_manager, "%").json() == []
    assert buscar(client, auth_manager, "M_ri").json() == []


def test_ca4_numero_enorme_no_rompe_la_busqueda(client, auth_manager, socios):
    assert buscar(client, auth_manager, "9" * 50).status_code == 200


def test_ca4_limit_y_offset(client, auth_manager, socios):
    respuesta = client.get(URL, params={"limit": 2, "offset": 1}, headers=auth_manager)

    assert nombres(respuesta) == ["Mariana López", "Mario Ruiz"]


def test_ca4_ficha_muestra_fecha_y_metas(client, auth_manager):
    socio = registrar(
        client, auth_manager, fecha_nacimiento="1995-03-15", metas="Bajar 5 kilos"
    ).json()

    ficha = client.get(f"{URL}/{socio['id']}", headers=auth_manager).json()

    assert ficha["fecha_nacimiento"] == "1995-03-15"
    assert ficha["metas"] == "Bajar 5 kilos"


def test_ca4_fecha_y_metas_son_opcionales(client, auth_manager):
    socio = registrar(client, auth_manager).json()

    ficha = client.get(f"{URL}/{socio['id']}", headers=auth_manager).json()

    assert ficha["fecha_nacimiento"] is None
    assert ficha["metas"] is None


# Regresión --------------------------------------------------------------------


def test_id_gigantesco_responde_422(client, auth_manager):
    assert client.get(f"{URL}/{10**30}", headers=auth_manager).status_code == 422


def test_nombre_se_guarda_sin_espacios_extremos(client, auth_manager, db_session):
    registrar(client, auth_manager, nombre="  Ana  ")

    assert db_session.scalar(select(Socio.nombre)) == "Ana"
