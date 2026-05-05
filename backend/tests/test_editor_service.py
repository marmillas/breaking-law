import uuid
import pytest
from datetime import datetime, UTC

from breaking_law.documents.editor_service import EditorService
from breaking_law.infra.models import EditorDraft, EditorDraftStatus, LawFirm, User, Document
from breaking_law.identity.security import PasswordHasher


@pytest.mark.asyncio
async def test_create_draft(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    draft = await service.create_draft(
        user_id=user.id,
        law_firm_id=firm.id,
        title="Motion to Dismiss",
    )
    assert draft.id is not None
    assert draft.user_id == user.id
    assert draft.law_firm_id == firm.id
    assert draft.title == "Motion to Dismiss"
    assert draft.status == EditorDraftStatus.draft
    assert draft.content == []


@pytest.mark.asyncio
async def test_autosave(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    draft = await service.create_draft(user.id, firm.id, "Draft")
    await db_session.commit()

    content = [
        {"type": "paragraph", "id": str(uuid.uuid4()), "content": "Hello world", "attrs": {}}
    ]
    updated = await service.autosave(draft.id, content)
    assert updated is not None
    assert updated.content == content
    assert updated.last_autosaved_at is not None


@pytest.mark.asyncio
async def test_autosave_not_found(db_session):
    service = EditorService(db_session)
    result = await service.autosave(uuid.uuid4(), [])
    assert result is None


@pytest.mark.asyncio
async def test_get_draft(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    draft = await service.create_draft(user.id, firm.id, "Draft")
    await db_session.commit()

    fetched = await service.get_draft(draft.id)
    assert fetched is not None
    assert fetched.id == draft.id


@pytest.mark.asyncio
async def test_get_draft_not_found(db_session):
    service = EditorService(db_session)
    fetched = await service.get_draft(uuid.uuid4())
    assert fetched is None


@pytest.mark.asyncio
async def test_list_drafts(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    await service.create_draft(user.id, firm.id, "Draft A")
    await service.create_draft(user.id, firm.id, "Draft B")
    await db_session.commit()

    drafts = await service.list_drafts(user.id, firm.id)
    assert len(drafts) == 2

    drafts = await service.list_drafts(user.id, firm.id, status=EditorDraftStatus.draft)
    assert len(drafts) == 2


@pytest.mark.asyncio
async def test_save_as_document(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    draft = await service.create_draft(user.id, firm.id, "Contract Draft")
    await db_session.commit()

    document = await service.save_as_document(draft.id, user.id)
    assert document is not None
    assert document.title == "Contract Draft"
    assert document.law_firm_id == firm.id
    assert document.owner_user_id == user.id

    # Draft should be linked and marked saved
    await db_session.refresh(draft)
    assert draft.document_id == document.id
    assert draft.status == EditorDraftStatus.saved


@pytest.mark.asyncio
async def test_save_as_document_not_found(db_session):
    service = EditorService(db_session)
    result = await service.save_as_document(uuid.uuid4(), uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_insert_citation(db_session):
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        email="user@example.com",
        full_name="Test User",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("pass"),
        role="assistant",
    )
    db_session.add(user)
    await db_session.flush()

    service = EditorService(db_session)
    draft = await service.create_draft(user.id, firm.id, "Draft")
    await db_session.commit()

    citation = {"type": "citation", "content": "Art. 1234 CC", "attrs": {"source": "civil_code"}}
    updated = await service.insert_citation(draft.id, citation)
    assert updated is not None
    assert len(updated.content) == 1
    assert updated.content[0]["type"] == "citation"
    assert "id" in updated.content[0]
    assert updated.last_autosaved_at is not None


@pytest.mark.asyncio
async def test_insert_citation_not_found(db_session):
    service = EditorService(db_session)
    result = await service.insert_citation(uuid.uuid4(), {"type": "citation", "content": "x"})
    assert result is None
