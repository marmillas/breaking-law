import pytest
import uuid

from breaking_law.infra.models import Document, DocumentACL, AccessLevel, User, LawFirm
from breaking_law.api.deps import UserContext
from breaking_law.documents.service import DocumentService
from breaking_law.shared.audit import AuditService
from breaking_law.documents.storage import Storage
from breaking_law.documents.parsing import DocumentParser


def _make_user_context(user_id: uuid.UUID, law_firm_id: uuid.UUID, role: str = "assistant") -> UserContext:
    return UserContext(
        user_id=user_id,
        law_firm_id=law_firm_id,
        email="test@example.com",
        role=role,
        full_name="Test User",
    )


@pytest.mark.asyncio
async def test_grant_and_revoke_access(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    db_session.add(owner)
    await db_session.flush()

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Test Doc")
    db_session.add(doc)
    await db_session.flush()

    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())

    acl = await service.grant_access(
        document_id=doc.id,
        user_id=None,
        role="paralegal",
        access_level=AccessLevel.read,
        law_firm_id=firm.id,
    )
    assert acl.role == "paralegal"
    assert acl.access_level == AccessLevel.read

    revoked = await service.revoke_access(acl.id, firm.id)
    assert revoked is True

    # Verify it's gone
    result = await db_session.execute(
        DocumentACL.__table__.select().where(DocumentACL.id == acl.id)
    )
    assert result.fetchone() is None


@pytest.mark.asyncio
async def test_user_without_access_gets_403(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner2@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    other = User(email="other@example.com", full_name="Other", law_firm_id=firm.id, hashed_password="x")
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Private Doc")
    db_session.add(doc)
    await db_session.flush()

    # Add explicit ACL that does NOT include 'other'
    acl = DocumentACL(document_id=doc.id, user_id=owner.id, access_level=AccessLevel.owner)
    db_session.add(acl)
    await db_session.flush()

    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())
    other_ctx = _make_user_context(other.id, firm.id)

    has_access = await service.check_document_access(other_ctx, doc.id, AccessLevel.read)
    assert has_access is False


@pytest.mark.asyncio
async def test_owner_always_has_access(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner3@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    db_session.add(owner)
    await db_session.flush()

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Owner Doc")
    db_session.add(doc)
    await db_session.flush()

    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())
    owner_ctx = _make_user_context(owner.id, firm.id)

    assert await service.check_document_access(owner_ctx, doc.id, AccessLevel.read) is True
    assert await service.check_document_access(owner_ctx, doc.id, AccessLevel.write) is True
    assert await service.check_document_access(owner_ctx, doc.id, AccessLevel.owner) is True


@pytest.mark.asyncio
async def test_role_based_access(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner4@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    lawyer = User(email="lawyer@example.com", full_name="Lawyer", law_firm_id=firm.id, role="lawyer", hashed_password="x")
    db_session.add(owner)
    db_session.add(lawyer)
    await db_session.flush()

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Role Doc")
    db_session.add(doc)
    await db_session.flush()

    acl = DocumentACL(document_id=doc.id, role="lawyer", access_level=AccessLevel.write)
    db_session.add(acl)
    await db_session.flush()

    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())
    lawyer_ctx = _make_user_context(lawyer.id, firm.id, role="lawyer")

    assert await service.check_document_access(lawyer_ctx, doc.id, AccessLevel.read) is True
    assert await service.check_document_access(lawyer_ctx, doc.id, AccessLevel.write) is True
    assert await service.check_document_access(lawyer_ctx, doc.id, AccessLevel.owner) is False


@pytest.mark.asyncio
async def test_acl_fallback_when_no_entries_exist(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner5@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    other = User(email="other2@example.com", full_name="Other", law_firm_id=firm.id, hashed_password="x")
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Fallback Doc")
    db_session.add(doc)
    await db_session.flush()

    # No ACL entries
    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())
    other_ctx = _make_user_context(other.id, firm.id)

    assert await service.check_document_access(other_ctx, doc.id, AccessLevel.read) is True
    assert await service.check_document_access(other_ctx, doc.id, AccessLevel.write) is True


@pytest.mark.asyncio
async def test_list_documents_respects_acl(db_session):
    firm = LawFirm(name="ACL Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(email="owner6@example.com", full_name="Owner", law_firm_id=firm.id, hashed_password="x")
    other = User(email="other3@example.com", full_name="Other", law_firm_id=firm.id, hashed_password="x")
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    doc1 = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Doc1")
    doc2 = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Doc2")
    db_session.add(doc1)
    db_session.add(doc2)
    await db_session.flush()

    # Add ACL for doc1 only, giving other read access
    acl = DocumentACL(document_id=doc1.id, user_id=other.id, access_level=AccessLevel.read)
    db_session.add(acl)
    await db_session.flush()

    # doc2 has no ACL entries -> fallback visible to all firm members
    service = DocumentService(db_session, None, AuditService(db_session), DocumentParser())
    other_ctx = _make_user_context(other.id, firm.id)

    docs = await service.list_documents(firm.id, other_ctx)
    doc_ids = {d.id for d in docs}
    assert doc1.id in doc_ids
    assert doc2.id in doc_ids

    # Now add an ACL to doc2 that excludes other -> doc2 should be hidden
    acl2 = DocumentACL(document_id=doc2.id, user_id=owner.id, access_level=AccessLevel.owner)
    db_session.add(acl2)
    await db_session.flush()

    docs = await service.list_documents(firm.id, other_ctx)
    doc_ids = {d.id for d in docs}
    assert doc1.id in doc_ids
    assert doc2.id not in doc_ids


@pytest.mark.asyncio
async def test_document_acl_endpoints(async_client, db_session):
    from breaking_law.identity.security import PasswordHasher

    firm = LawFirm(name="ACL Endpoint Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(
        email="aclowner@example.com",
        full_name="ACL Owner",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
        role="owner",
    )
    other = User(
        email="aclother@example.com",
        full_name="ACL Other",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    # Login as owner
    login_resp = await async_client.post(
        "/auth/login",
        data={"username": "aclowner@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    owner_token = login_resp.json()["access_token"]

    # Create a document
    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Endpoint Doc")
    db_session.add(doc)
    await db_session.flush()

    # Grant access to other user
    grant_resp = await async_client.post(
        f"/documents/{doc.id}/acl",
        json={"user_id": str(other.id), "access_level": "read"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert grant_resp.status_code == 201
    acl_data = grant_resp.json()
    assert acl_data["user_id"] == str(other.id)
    assert acl_data["access_level"] == "read"

    # List ACL
    list_resp = await async_client.get(
        f"/documents/{doc.id}/acl",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Revoke ACL
    revoke_resp = await async_client.delete(
        f"/documents/{doc.id}/acl/{acl_data['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert revoke_resp.status_code == 204

    # Verify ACL list is empty
    list_resp2 = await async_client.get(
        f"/documents/{doc.id}/acl",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert list_resp2.status_code == 200
    assert len(list_resp2.json()) == 0


@pytest.mark.asyncio
async def test_non_owner_cannot_grant_acl(async_client, db_session):
    from breaking_law.identity.security import PasswordHasher

    firm = LawFirm(name="ACL Deny Firm")
    db_session.add(firm)
    await db_session.flush()

    owner = User(
        email="denyowner@example.com",
        full_name="Deny Owner",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    other = User(
        email="denyother@example.com",
        full_name="Deny Other",
        law_firm_id=firm.id,
        hashed_password=PasswordHasher.hash_password("secret123"),
    )
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    # Login as other
    login_resp = await async_client.post(
        "/auth/login",
        data={"username": "denyother@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    other_token = login_resp.json()["access_token"]

    doc = Document(law_firm_id=firm.id, owner_user_id=owner.id, title="Deny Doc")
    db_session.add(doc)
    await db_session.flush()

    grant_resp = await async_client.post(
        f"/documents/{doc.id}/acl",
        json={"user_id": str(other.id), "access_level": "read"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert grant_resp.status_code == 403
