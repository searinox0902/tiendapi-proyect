import pytest


@pytest.fixture
def provider_id(client, auth_headers) -> str:
    """Una Referencia exige `provider_id`, así que primero hay que crear el proveedor."""
    r = client.post(
        "/api/v1/providers/", json={"title": "Distribuidora Test"}, headers=auth_headers
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create(client, headers, provider_id, sku, title, base_price="1000.00", brand=None):
    r = client.post(
        "/api/v1/references/",
        json={
            "provider_id": provider_id,
            "sku": sku,
            "title": title,
            "brand": brand,
            "base_price": base_price,
            "iva_percentage": "19.00",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_list_references_scoped_empty(client, auth_headers):
    """Un negocio recién creado ve una página vacía (aislamiento por tenant, D-23)."""
    r = client.get("/api/v1/references/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "skip": 0, "limit": 50}


def test_references_requires_auth(client):
    """Sin token Bearer la API responde 401 (auth real, cierra A-12)."""
    r = client.get("/api/v1/references/")
    assert r.status_code == 401


def test_filter_by_sku_is_partial_and_case_insensitive(client, auth_headers, provider_id):
    _create(client, auth_headers, provider_id, "FRE-0001", "Pastillas de freno")
    _create(client, auth_headers, provider_id, "MOT-0001", "Bujía de encendido")

    r = client.get("/api/v1/references/", params={"sku": "fre"}, headers=auth_headers)
    body = r.json()

    assert body["total"] == 1
    assert [i["sku"] for i in body["items"]] == ["FRE-0001"]


def test_filter_by_title_is_partial_and_case_insensitive(client, auth_headers, provider_id):
    _create(client, auth_headers, provider_id, "FRE-0001", "Pastillas de freno")
    _create(client, auth_headers, provider_id, "MOT-0001", "Bujía de encendido")

    r = client.get("/api/v1/references/", params={"title": "BUJÍA"}, headers=auth_headers)
    body = r.json()

    assert body["total"] == 1
    assert body["items"][0]["sku"] == "MOT-0001"


def test_filters_combine_with_and(client, auth_headers, provider_id):
    _create(client, auth_headers, provider_id, "FRE-0001", "Pastillas de freno")
    _create(client, auth_headers, provider_id, "FRE-0002", "Disco de freno")

    r = client.get(
        "/api/v1/references/",
        params={"sku": "FRE", "title": "Disco"},
        headers=auth_headers,
    )
    body = r.json()

    assert body["total"] == 1
    assert body["items"][0]["sku"] == "FRE-0002"


def test_pagination_does_not_repeat_rows_and_total_ignores_limit(
    client, auth_headers, provider_id
):
    """`total` cuenta el filtro completo; las páginas no se solapan."""
    for n in range(1, 6):
        _create(client, auth_headers, provider_id, f"SKU-{n:04d}", f"Repuesto {n}")

    first = client.get(
        "/api/v1/references/", params={"skip": 0, "limit": 2}, headers=auth_headers
    ).json()
    second = client.get(
        "/api/v1/references/", params={"skip": 2, "limit": 2}, headers=auth_headers
    ).json()

    assert first["total"] == 5 and second["total"] == 5
    assert len(first["items"]) == 2 and len(second["items"]) == 2

    seen = [i["sku"] for i in first["items"]] + [i["sku"] for i in second["items"]]
    assert len(set(seen)) == 4, "una fila apareció en dos páginas"


def test_like_wildcards_in_the_query_are_escaped(client, auth_headers, provider_id):
    """Buscar `%` debe buscar el carácter, no actuar como comodín."""
    _create(client, auth_headers, provider_id, "OFERTA-50%", "Kit con descuento")
    _create(client, auth_headers, provider_id, "NORMAL-001", "Kit sin descuento")

    r = client.get("/api/v1/references/", params={"sku": "%"}, headers=auth_headers)
    body = r.json()

    assert body["total"] == 1
    assert body["items"][0]["sku"] == "OFERTA-50%"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"skip": -1}])
def test_rejects_out_of_range_pagination(client, auth_headers, params):
    r = client.get("/api/v1/references/", params=params, headers=auth_headers)
    assert r.status_code == 422


def test_summary_on_empty_catalog(client, auth_headers):
    r = client.get("/api/v1/references/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()

    assert body["total_references"] == 0
    assert body["total_brands"] == 0
    assert body["last_updated_at"] is None
    assert body["latest"] == []


def test_summary_counts_distinct_brands_ignoring_nulls(client, auth_headers, provider_id):
    _create(client, auth_headers, provider_id, "A-1", "Pastillas", brand="Brembo")
    _create(client, auth_headers, provider_id, "A-2", "Disco", brand="Brembo")
    _create(client, auth_headers, provider_id, "A-3", "Bujía", brand="NGK")
    _create(client, auth_headers, provider_id, "A-4", "Genérico", brand=None)

    body = client.get("/api/v1/references/summary", headers=auth_headers).json()

    assert body["total_references"] == 4
    # Brembo aparece dos veces y el genérico no tiene marca: quedan 2 distintas.
    assert body["total_brands"] == 2
    assert body["last_updated_at"] is not None


def test_summary_latest_is_newest_first_and_capped(client, auth_headers, provider_id):
    """La card muestra las últimas creadas, no las primeras por SKU."""
    for n in range(1, 6):
        _create(client, auth_headers, provider_id, f"SKU-{n}", f"Repuesto {n}")

    body = client.get(
        "/api/v1/references/summary", params={"latest": 3}, headers=auth_headers
    ).json()

    assert body["total_references"] == 5
    assert [i["sku"] for i in body["latest"]] == ["SKU-5", "SKU-4", "SKU-3"]
    # La card solo necesita estos campos.
    assert set(body["latest"][0]) == {"id", "sku", "title", "base_price"}


def test_summary_is_scoped_by_tenant(client, auth_headers, provider_id):
    """Otro negocio no ve el catálogo ajeno en sus totales (D-23)."""
    _create(client, auth_headers, provider_id, "MIO-1", "Mi repuesto", brand="NGK")

    import uuid as _uuid

    otro_email = f"otro_{_uuid.uuid4().hex[:8]}@test.co"
    client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Otro Negocio", "full_name": "O",
            "email": otro_email, "password": "secret123",
        },
    )
    otro_token = client.post(
        "/api/v1/auth/login", json={"email": otro_email, "password": "secret123"}
    ).json()["access_token"]

    body = client.get(
        "/api/v1/references/summary",
        headers={"Authorization": f"Bearer {otro_token}"},
    ).json()

    assert body["total_references"] == 0
    assert body["total_brands"] == 0


def test_summary_requires_auth(client):
    assert client.get("/api/v1/references/summary").status_code == 401
