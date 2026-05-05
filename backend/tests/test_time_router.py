import uuid
import pytest
import pytest_asyncio

from breaking_law.infra.models import LawFirm, User, TimeEntry, TimeEntryStatus
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="timetest@example.com",
        full_name="Time Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "timetest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_time_start_requires_auth(async_client):
    response = await async_client.post("/time/start", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_time_start_stop(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post(
        "/time/start",
        json={"description": "Research"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    entry_id = uuid.UUID(data["id"])
    assert data["status"] == "draft"
    assert data["ended_at"] is None

    response = await async_client.post(
        f"/time/{entry_id}/stop",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ended_at"] is not None
    assert data["duration_minutes"] is not None


@pytest.mark.asyncio
async def test_time_list_entries(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    # Start two timers
    await async_client.post("/time/start", json={"description": "A"}, headers=headers)
    await async_client.post("/time/start", json={"description": "B"}, headers=headers)

    response = await async_client.get("/time/entries", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_time_submit_and_approve(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post("/time/start", json={}, headers=headers)
    entry_id = uuid.UUID(response.json()["id"])
    await async_client.post(f"/time/{entry_id}/stop", headers=headers)

    response = await async_client.post(f"/time/{entry_id}/submit", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"

    response = await async_client.post(f"/time/{entry_id}/approve", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_time_report(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    # Create and approve an entry
    response = await async_client.post("/time/start", json={"description": "Billable"}, headers=headers)
    entry_id = uuid.UUID(response.json()["id"])
    await async_client.post(f"/time/{entry_id}/stop", headers=headers)
    await async_client.post(f"/time/{entry_id}/submit", headers=headers)
    await async_client.post(f"/time/{entry_id}/approve", headers=headers)

    response = await async_client.get("/time/report", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_hours" in data
    assert "billable_hours" in data
    assert "matter_breakdown" in data


@pytest.mark.asyncio
async def test_time_stop_not_found(async_client, auth_headers):
    headers, _, _ = auth_headers
    response = await async_client.post(f"/time/{uuid.uuid4()}/stop", headers=headers)
    assert response.status_code == 404
