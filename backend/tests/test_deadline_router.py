import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC

from breaking_law.infra.models import LawFirm, User, Deadline, DeadlineStatus
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="deadlinetest@example.com",
        full_name="Deadline Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "deadlinetest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_deadline_create_requires_auth(async_client):
    response = await async_client.post("/deadlines/", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deadline_crud(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()

    response = await async_client.post(
        "/deadlines/",
        json={"title": "File motion", "due_date": due, "priority": "high"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    deadline_id = uuid.UUID(data["id"])
    assert data["title"] == "File motion"
    assert data["status"] == "pending"

    response = await async_client.get("/deadlines/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await async_client.post(f"/deadlines/{deadline_id}/acknowledge", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"

    response = await async_client.post(f"/deadlines/{deadline_id}/complete", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_deadline_overdue(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    # Create overdue deadline directly in DB
    deadline = Deadline(
        law_firm_id=firm_id,
        created_by=user_id,
        title="Overdue task",
        due_date=datetime.now(UTC) - timedelta(days=1),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)
    await db_session.commit()

    response = await async_client.get("/deadlines/overdue", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Overdue task"


@pytest.mark.asyncio
async def test_deadline_upcoming(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    deadline = Deadline(
        law_firm_id=firm_id,
        created_by=user_id,
        title="Upcoming task",
        due_date=datetime.now(UTC) + timedelta(days=2),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)
    await db_session.commit()

    response = await async_client.get("/deadlines/upcoming?days=7", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Upcoming task"
