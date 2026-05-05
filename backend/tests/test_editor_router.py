import uuid
import pytest
import pytest_asyncio

from breaking_law.infra.models import LawFirm, User, EditorDraft, EditorDraftStatus
from breaking_law.identity.security import PasswordHasher


@pytest_asyncio.fixture
async def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="editortest@example.com",
        full_name="Editor Test",
        hashed_password=PasswordHasher.hash_password("secret"),
        law_firm_id=firm.id,
        role="owner",
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        data={"username": "editortest@example.com", "password": "secret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, firm.id, user.id


@pytest.mark.asyncio
async def test_editor_create_requires_auth(async_client):
    response = await async_client.post("/editor/drafts", json={"title": "Draft"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_editor_create_and_get(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post(
        "/editor/drafts",
        json={"title": "Motion to Dismiss"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    draft_id = uuid.UUID(data["id"])
    assert data["title"] == "Motion to Dismiss"
    assert data["status"] == "draft"
    assert data["content"] == []

    response = await async_client.get(f"/editor/drafts/{draft_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(draft_id)


@pytest.mark.asyncio
async def test_editor_autosave(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post(
        "/editor/drafts",
        json={"title": "Draft"},
        headers=headers,
    )
    draft_id = uuid.UUID(response.json()["id"])

    content = [
        {"type": "paragraph", "id": str(uuid.uuid4()), "content": "Hello", "attrs": {}}
    ]
    response = await async_client.put(
        f"/editor/drafts/{draft_id}/autosave",
        json={"content": content},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == content
    assert data["last_autosaved_at"] is not None


@pytest.mark.asyncio
async def test_editor_list_drafts(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    await async_client.post("/editor/drafts", json={"title": "A"}, headers=headers)
    await async_client.post("/editor/drafts", json={"title": "B"}, headers=headers)

    response = await async_client.get("/editor/drafts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_editor_save_as_document(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post(
        "/editor/drafts",
        json={"title": "Contract"},
        headers=headers,
    )
    draft_id = uuid.UUID(response.json()["id"])

    response = await async_client.post(
        f"/editor/drafts/{draft_id}/save-as-document",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Contract"
    assert data["law_firm_id"] == str(firm_id)


@pytest.mark.asyncio
async def test_editor_insert_citation(async_client, auth_headers, db_session):
    headers, firm_id, user_id = auth_headers

    response = await async_client.post(
        "/editor/drafts",
        json={"title": "Draft"},
        headers=headers,
    )
    draft_id = uuid.UUID(response.json()["id"])

    citation = {"type": "citation", "content": "Art. 1234 CC", "attrs": {}}
    response = await async_client.post(
        f"/editor/drafts/{draft_id}/insert-citation",
        json={"citation_block": citation},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["content"]) == 1
    assert data["content"][0]["type"] == "citation"


@pytest.mark.asyncio
async def test_editor_get_not_found(async_client, auth_headers):
    headers, _, _ = auth_headers
    response = await async_client.get(f"/editor/drafts/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
