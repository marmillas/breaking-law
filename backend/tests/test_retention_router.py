import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC

from breaking_law.infra.models import LawFirm, User, Document
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="retentiontest@example.com",
        full_name="Retention Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "retentiontest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_retention_policy_requires_auth(async_client):
    response = await async_client.post("/retention/123/policy", json={"policy": "keep_forever"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_retention_set_policy(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    doc = Document(
        law_firm_id=firm_id,
        owner_user_id=user_id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.post(
        f"/retention/{doc.id}/policy",
        json={"policy": "keep_forever"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["retention_policy"] == "keep_forever"
    assert data["deletion_date"] is None


@pytest.mark.asyncio
async def test_retention_schedule_deletion(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    doc = Document(
        law_firm_id=firm_id,
        owner_user_id=user_id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.commit()

    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    response = await async_client.post(
        f"/retention/{doc.id}/schedule-deletion",
        json={"deletion_date": future},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deletion_date"] is not None


@pytest.mark.asyncio
async def test_retention_policy_not_found(async_client, auth_headers):
    headers, _, _ = auth_headers
    response = await async_client.post(
        f"/retention/{uuid.uuid4()}/policy",
        json={"policy": "keep_forever"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retention_policy_requires_owner_role(async_client, db_session):
    firm = LawFirm(name="Test Firm 2")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="assistant@example.com",
        full_name="Assistant",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="assistant",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "assistant@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    doc = Document(
        law_firm_id=firm.id,
        owner_user_id=user.id,
        title="Contract",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.post(
        f"/retention/{doc.id}/policy",
        json={"policy": "keep_forever"},
        headers=headers,
    )
    assert response.status_code == 403
