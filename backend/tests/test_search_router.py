import pytest
import uuid
from unittest.mock import patch

from breaking_law.infra.models import Document, DocumentVersion, DocumentChunk, ParserStatus, LawFirm, User
from breaking_law.identity.service import AuthService


@pytest.mark.asyncio
async def test_search_endpoint_requires_auth(async_client):
    """Search endpoint must return 401 without a valid token."""
    response = await async_client.post("/search", json={"query": "contract"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_endpoint_returns_results(async_client, db_session):
    """Basic end-to-end search with authenticated user."""
    # Create law firm and user
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        law_firm_id=firm.id,
        email="search@example.com",
        full_name="Search User",
        hashed_password="$2b$12$...",
        role="assistant",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Generate JWT token
    auth_service = AuthService(
        secret_key="insecure-key-for-development",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )
    token = auth_service.create_access_token(
        data={
            "sub": str(user.id),
            "firm_id": str(firm.id),
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
        }
    )

    # Mock SearchService to avoid SQLite/pgvector incompatibility
    mock_result = [
        type(
            "R",
            (),
            {
                "document_id": uuid.uuid4(),
                "document_title": "Contract Draft",
                "chunk_text": "contract terms",
                "score": 0.95,
                "matter_id": None,
            },
        )()
    ]

    with patch("breaking_law.search.router.SearchService.hybrid_search", return_value=mock_result):
        response = await async_client.post(
            "/search",
            json={"query": "contract", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["document_title"] == "Contract Draft"


@pytest.mark.asyncio
async def test_suggestions_endpoint(async_client, db_session):
    """Suggestions endpoint returns quick results for authenticated users."""
    firm = LawFirm(name="Test Firm")
    db_session.add(firm)
    await db_session.flush()

    user = User(
        law_firm_id=firm.id,
        email="suggest@example.com",
        full_name="Suggest User",
        hashed_password="$2b$12$...",
        role="assistant",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    auth_service = AuthService(
        secret_key="insecure-key-for-development",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )
    token = auth_service.create_access_token(
        data={
            "sub": str(user.id),
            "firm_id": str(firm.id),
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
        }
    )

    mock_suggestions = ["monthly lease payment", "lease termination clause"]

    with patch(
        "breaking_law.search.router.SearchService.quick_suggestions",
        return_value=mock_suggestions,
    ):
        response = await async_client.get(
            "/search/suggestions?q=lease",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert data["suggestions"] == mock_suggestions
