import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC

from breaking_law.infra.models import LawFirm, User, Deadline, DeadlineStatus, TimeEntry, TimeEntryStatus
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="calendartest@example.com",
        full_name="Calendar Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "calendartest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_calendar_deadlines_requires_auth(async_client):
    response = await async_client.get("/calendar/deadlines.ics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_calendar_deadlines_ical(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    deadline = Deadline(
        law_firm_id=firm_id,
        created_by=user_id,
        title="Court Date",
        description="Hearing on motion",
        due_date=datetime.now(UTC) + timedelta(days=3),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)
    await db_session.commit()

    response = await async_client.get("/calendar/deadlines.ics", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    body = response.text
    assert "BEGIN:VCALENDAR" in body
    assert "Court Date" in body
    assert "END:VCALENDAR" in body


@pytest.mark.asyncio
async def test_calendar_time_entries_ical(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    entry = TimeEntry(
        law_firm_id=firm_id,
        user_id=user_id,
        description="Deposition prep",
        started_at=datetime.now(UTC) - timedelta(hours=2),
        ended_at=datetime.now(UTC) - timedelta(hours=1),
        duration_minutes=60,
        status=TimeEntryStatus.approved,
    )
    db_session.add(entry)
    await db_session.commit()

    response = await async_client.get("/calendar/time-entries.ics", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    body = response.text
    assert "BEGIN:VCALENDAR" in body
    assert "Deposition prep" in body
    assert "END:VCALENDAR" in body


@pytest.mark.asyncio
async def test_calendar_matter_ical(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers
    matter_id = uuid.uuid4()

    deadline = Deadline(
        law_firm_id=firm_id,
        created_by=user_id,
        matter_id=matter_id,
        title="Matter Deadline",
        due_date=datetime.now(UTC) + timedelta(days=2),
        status=DeadlineStatus.pending,
    )
    db_session.add(deadline)

    entry = TimeEntry(
        law_firm_id=firm_id,
        user_id=user_id,
        matter_id=matter_id,
        description="Matter work",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        ended_at=datetime.now(UTC),
        duration_minutes=60,
        status=TimeEntryStatus.draft,
    )
    db_session.add(entry)
    await db_session.commit()

    response = await async_client.get(f"/calendar/matter/{matter_id}.ics", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    body = response.text
    assert "Matter Deadline" in body
    assert "Matter work" in body
    assert "END:VCALENDAR" in body
