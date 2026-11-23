"""Configuración global de fixtures para Pytest."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import get_password_hash
from app.db.base import Base
from app.main import app
from app.models.gym import Gym
from app.models.user import User, UserRole

# Configurar base de datos SQLite en memoria para pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest.fixture(scope="function")
def db_session():
    """Crea una base de datos limpia en memoria para cada test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # 1. Crear Gimnasio de prueba (ID 1)
    test_gym = Gym(
        id=1,
        name="Gym de Prueba",
        location="Calle Test 123",
        base_enrollment_fee=50.0,
    )
    session.add(test_gym)

    # 2. Crear Usuario Admin (ID 1)
    admin_user = User(
        id=1,
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    admin_user.gyms.append(test_gym)
    session.add(admin_user)

    # 3. Crear Usuario Manager (ID 2) asignado al Gym 1
    manager_user = User(
        id=2,
        email="manager@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        is_active=True,
    )
    manager_user.gyms.append(test_gym)
    session.add(manager_user)

    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP de prueba con la base de datos sobrescrita."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()