import pytest
from fastapi.testclient import TestClient

from app.core.database import engine
from app.main import app
from app.models import Base


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """
    Crea el esquema a partir de los modelos antes de la suite.

    Requiere una BBDD PostgreSQL accesible vía `DATABASE_URL`. En CI la provee
    el service de Postgres del workflow; en local, levanta `docker compose up -d
    postgres` primero. `checkfirst=True` (default) hace idempotente la creación
    si las tablas ya existen por `alembic upgrade head`.
    """
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Registra un negocio de prueba y devuelve el header Bearer de su propietario."""
    import uuid

    email = f"user_{uuid.uuid4().hex[:8]}@test.co"
    client.post(
        "/api/v1/auth/register",
        json={"business_name": "Fixture Biz", "full_name": "U", "email": email, "password": "secret123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
