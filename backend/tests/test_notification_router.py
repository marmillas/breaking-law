import uuid
import pytest
import pytest_asyncio

from breaking_law.infra.models import LawFirm, User, Notification, DeadlinePriority
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="notiftest@example.com",
        full_name="Notification Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "notiftest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_notifications_list_requires_auth(async_client):
    response = await async_client.get("/notifications/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_notifications_list_unread(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    # Seed notifications directly
    for i in range(3):
        n = Notification(
            law_firm_id=firm_id,
            user_id=user_id,
            title=f"Notif {i}",
            message=f"Message {i}",
            read=False,
        )
        db_session.add(n)
    await db_session.commit()

    response = await async_client.get("/notifications/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_notifications_mark_read(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    n = Notification(
        law_firm_id=firm_id,
        user_id=user_id,
        title="Read me",
        message="Please",
        read=False,
    )
    db_session.add(n)
    await db_session.commit()

    response = await async_client.post(f"/notifications/{n.id}/read", headers=headers)
    assert response.status_code == 200
    assert response.json()["read"] is True


@pytest.mark.asyncio
async def test_notifications_mark_all_read(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    for i in range(2):
        n = Notification(
            law_firm_id=firm_id,
            user_id=user_id,
            title=f"N{i}",
            message="M",
            read=False,
        )
        db_session.add(n)
    await db_session.commit()

    response = await async_client.post("/notifications/read-all", headers=headers)
    assert response.status_code == 200
    assert response.json()["marked_count"] == 2

    response = await async_client.get("/notifications/", headers=headers)
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_notifications_urgent(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    n1 = Notification(
        law_firm_id=firm_id,
        user_id=user_id,
        title="Critical",
        message="Urgent",
        priority=DeadlinePriority.critical,
        read=False,
    )
    n2 = Notification(
        law_firm_id=firm_id,
        user_id=user_id,
        title="Low",
        message="Not urgent",
        priority=DeadlinePriority.low,
        read=False,
    )
    db_session.add_all([n1, n2])
    await db_session.commit()

    response = await async_client.get("/notifications/urgent", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Critical"
