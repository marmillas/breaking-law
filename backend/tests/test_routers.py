import pytest
from breaking_law.infra.models import LawFirm, User
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to Breaking Law API"


@pytest.mark.asyncio
async def test_protected_endpoint_returns_401(async_client):
    response = await async_client.get("/clients/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tenant_isolation(async_client, db_session):
    # Create two law firms
    firm1 = LawFirm(name="Firm One")
    firm2 = LawFirm(name="Firm Two")
    db_session.add_all([firm1, firm2])
    await db_session.flush()

    # Create users
    user1 = User(
        email="u1@example.com",
        full_name="User One",
        law_firm_id=firm1.id,
        hashed_password=PasswordHasher.hash_password("pass1"),
        role="owner",
    )
    user2 = User(
        email="u2@example.com",
        full_name="User Two",
        law_firm_id=firm2.id,
        hashed_password=PasswordHasher.hash_password("pass2"),
        role="owner",
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Login as user1
    resp = await async_client.post(
        "/auth/login", data={"username": "u1@example.com", "password": "pass1"}
    )
    assert resp.status_code == 200
    token1 = resp.json()["access_token"]

    # Login as user2
    resp = await async_client.post(
        "/auth/login", data={"username": "u2@example.com", "password": "pass2"}
    )
    assert resp.status_code == 200
    token2 = resp.json()["access_token"]

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Create client as user1
    resp = await async_client.post(
        "/clients/",
        json={"name": "Client A", "email": "a@example.com"},
        headers=headers1,
    )
    assert resp.status_code == 201
    client_a_id = resp.json()["id"]

    # Create client as user2
    resp = await async_client.post(
        "/clients/",
        json={"name": "Client B", "email": "b@example.com"},
        headers=headers2,
    )
    assert resp.status_code == 201
    client_b_id = resp.json()["id"]

    # List clients for user1
    resp = await async_client.get("/clients/", headers=headers1)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == client_a_id

    # List clients for user2
    resp = await async_client.get("/clients/", headers=headers2)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == client_b_id

    # Cross-tenant access should return 404
    resp = await async_client.get(f"/clients/{client_b_id}", headers=headers1)
    assert resp.status_code == 404

    resp = await async_client.get(f"/clients/{client_a_id}", headers=headers2)
    assert resp.status_code == 404
