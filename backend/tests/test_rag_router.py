"""
Tests for the RAG and retrieval routers.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from breaking_law.search.llm import LLMResponse
from breaking_law.domain.schemas.search import RetrievalResult
from breaking_law.search.rag_service import RAGResponse, SourceAttribution
from breaking_law.search.citation import CitationReport


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers(async_client, db_session):
    """Create a user and law firm, return auth headers."""
    import asyncio
    from breaking_law.infra.models import User, LawFirm
    from breaking_law.identity.security import PasswordHasher

    async def _setup():
        firm = LawFirm(name="Test Firm")
        db_session.add(firm)
        await db_session.flush()

        user = User(
            email="ragtest@example.com",
            full_name="RAG Test",
            hashed_password=PasswordHasher.hash_password("secret"),
            law_firm_id=firm.id,
            role="lawyer",
        )
        db_session.add(user)
        await db_session.commit()

        # Login to get token
        response = await async_client.post(
            "/auth/login",
            data={"username": "ragtest@example.com", "password": "secret"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, firm.id, user.id

    return asyncio.run(_setup())


# ---------------------------------------------------------------------------
# Retrieval router tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieval_context_requires_auth(async_client):
    """Retrieval endpoint requires authentication."""
    response = await async_client.post("/retrieval/context", json={"query": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_retrieval_context_returns_results(async_client, auth_headers):
    """Retrieval endpoint returns retrieved chunks."""
    headers, firm_id, user_id = auth_headers
    doc_id = uuid.uuid4()

    mock_result = [
        RetrievalResult(
            chunk_text="Article 1254 governs contracts.",
            document_id=doc_id,
            document_title="Civil Code",
            matter_id=None,
            score=0.85,
            source_type="document",
        ),
    ]

    with patch(
        "breaking_law.search.retrieval_service.RetrievalService.retrieve_context_for_user",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        response = await async_client.post(
            "/retrieval/context",
            json={"query": "contracts", "top_k": 3, "min_similarity": 0.75},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["document_title"] == "Civil Code"


@pytest.mark.asyncio
async def test_retrieval_context_rejects_empty_query(async_client, auth_headers):
    """Retrieval endpoint rejects empty queries."""
    headers, _, _ = auth_headers
    response = await async_client.post(
        "/retrieval/context",
        json={"query": "  ", "top_k": 3},
        headers=headers,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# RAG router tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_query_requires_auth(async_client):
    """RAG query endpoint requires authentication."""
    response = await async_client.post("/rag/query", json={"query": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rag_query_returns_response(async_client, auth_headers):
    """RAG query endpoint returns full response with answer and sources."""
    headers, firm_id, user_id = auth_headers
    doc_id = uuid.uuid4()

    mock_rag_response = RAGResponse(
        answer="Contracts are governed by Article 1254.",
        sources=[
            SourceAttribution(
                document_id=doc_id,
                document_title="Civil Code",
                chunk_text="Article 1254 governs contracts.",
                score=0.90,
            )
        ],
        citation_report=CitationReport(
            validated=[],
            unverified=[],
            has_unverified=False,
            confidence_score=1.0,
        ),
        needs_review=False,
        confidence=1.0,
    )

    with patch(
        "breaking_law.search.rag_service.RAGService.query",
        new_callable=AsyncMock,
        return_value=mock_rag_response,
    ):
        response = await async_client.post(
            "/rag/query",
            json={"query": "What governs contracts?", "task_type": "analyze"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "citation_report" in data
    assert "needs_review" in data
    assert "confidence" in data
    assert data["answer"] == "Contracts are governed by Article 1254."
    assert data["needs_review"] is False


@pytest.mark.asyncio
async def test_rag_query_rejects_empty_query(async_client, auth_headers):
    """RAG query endpoint rejects empty queries."""
    headers, _, _ = auth_headers
    response = await async_client.post(
        "/rag/query",
        json={"query": "  ", "task_type": "analyze"},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rag_query_rejects_invalid_task_type(async_client, auth_headers):
    """RAG query endpoint rejects invalid task types."""
    headers, _, _ = auth_headers
    response = await async_client.post(
        "/rag/query",
        json={"query": "test", "task_type": "invalid"},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rag_query_accepts_all_valid_task_types(async_client, auth_headers):
    """RAG query accepts all valid task types."""
    headers, _, _ = auth_headers

    mock_rag_response = RAGResponse(
        answer="Answer",
        sources=[],
        citation_report=CitationReport(
            validated=[],
            unverified=[],
            has_unverified=False,
            confidence_score=1.0,
        ),
        needs_review=False,
        confidence=1.0,
    )

    for task_type in ["draft", "review", "summarize", "checklist", "analyze"]:
        with patch(
            "breaking_law.search.rag_service.RAGService.query",
            new_callable=AsyncMock,
            return_value=mock_rag_response,
        ):
            response = await async_client.post(
                "/rag/query",
                json={"query": "Test", "task_type": task_type},
                headers=headers,
            )
        assert response.status_code == 200, f"Failed for task_type={task_type}"
