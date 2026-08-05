import uuid


def _register(client, email: str):
    return client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Test Biz",
            "full_name": "Owner",
            "email": email,
            "password": "secret123",
        },
    )


def test_register_login_and_me(client):
    email = f"owner_{uuid.uuid4().hex[:8]}@test.co"

    r = _register(client, email)
    assert r.status_code == 201
    assert r.json()["role"] == "owner"

    r = client.post("/api/v1/auth/login", json={"email": email, "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_login_wrong_password(client):
    email = f"u_{uuid.uuid4().hex[:8]}@test.co"
    _register(client, email)
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "nope"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client):
    email = f"dup_{uuid.uuid4().hex[:8]}@test.co"
    assert _register(client, email).status_code == 201
    assert _register(client, email).status_code == 409


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_seat_limit_enforced(client):
    email = f"seat_{uuid.uuid4().hex[:8]}@test.co"
    _register(client, email)
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "secret123"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}

    # owner ya es asiento 1; se pueden crear 2 más, el 4º debe fallar
    for i in range(2):
        r = client.post(
            "/api/v1/auth/users",
            headers=headers,
            json={
                "full_name": f"Sub {i}",
                "email": f"sub_{uuid.uuid4().hex[:8]}@test.co",
                "password": "secret123",
            },
        )
        assert r.status_code == 201

    r = client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={
            "full_name": "Sub extra",
            "email": f"sub_{uuid.uuid4().hex[:8]}@test.co",
            "password": "secret123",
        },
    )
    assert r.status_code == 409
