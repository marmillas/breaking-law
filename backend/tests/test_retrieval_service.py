"""
Tests for the retrieval service.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from breaking_law.api.deps import UserContext
from breaking_law.search.retrieval_service import RetrievalService, RetrievalResult
from breaking_law.search.search_service import SearchResult


@pytest.fixture
def mock_user():
    return UserContext(
        user_id=uuid.uuid4(),
        law_firm_id=uuid.uuid4(),
        email="test@example.com",
        role="lawyer",
        full_name="Test User",
    )


@pytest.fixture
def mock_search_service():
    svc = MagicMock()
    svc.hybrid_search = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_retrieve_context_returns_results(mock_search_service, mock_user):
    """Retrieval returns filtered and sorted results above threshold."""
    doc_id = uuid.uuid4()
    matter_id = uuid.uuid4()
    mock_search_service.hybrid_search.return_value = [
        SearchResult(
            document_id=doc_id,
            document_title="Contract A",
            chunk_text="Article 5 states...",
            score=0.85,
            matter_id=matter_id,
        ),
        SearchResult(
            document_id=doc_id,
            document_title="Contract B",
            chunk_text="Article 6 states...",
            score=0.60,
            matter_id=None,
        ),
    ]

    retrieval = RetrievalService(mock_search_service)
    results = await retrieval.retrieve_context_for_user(
        query="contract termination",
        law_firm_id=mock_user.law_firm_id,
        user=mock_user,
        top_k=5,
        min_similarity=0.75,
    )

    assert len(results) == 1
    assert results[0].score == 0.85
    assert results[0].chunk_text == "Article 5 states..."
    mock_search_service.hybrid_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieve_context_filters_below_threshold(mock_search_service, mock_user):
    """Results below min_similarity are discarded."""
    doc_id = uuid.uuid4()
    mock_search_service.hybrid_search.return_value = [
        SearchResult(
            document_id=doc_id,
            document_title="Low Relevance",
            chunk_text="Some text",
            score=0.50,
            matter_id=None,
        ),
    ]

    retrieval = RetrievalService(mock_search_service)
    results = await retrieval.retrieve_context_for_user(
        query="irrelevant",
        law_firm_id=mock_user.law_firm_id,
        user=mock_user,
        top_k=5,
        min_similarity=0.75,
    )

    assert results == []


@pytest.mark.asyncio
async def test_retrieve_context_empty_search(mock_search_service, mock_user):
    """Empty search results return empty list."""
    mock_search_service.hybrid_search.return_value = []

    retrieval = RetrievalService(mock_search_service)
    results = await retrieval.retrieve_context_for_user(
        query="nonexistent",
        law_firm_id=mock_user.law_firm_id,
        user=mock_user,
    )

    assert results == []


@pytest.mark.asyncio
async def test_retrieve_context_respects_top_k(mock_search_service, mock_user):
    """Only top_k results are returned even if more pass threshold."""
    doc_id = uuid.uuid4()
    mock_search_service.hybrid_search.return_value = [
        SearchResult(
            document_id=doc_id,
            document_title=f"Doc {i}",
            chunk_text=f"Chunk {i}",
            score=0.90 - (i * 0.01),
            matter_id=None,
        )
        for i in range(10)
    ]

    retrieval = RetrievalService(mock_search_service)
    results = await retrieval.retrieve_context_for_user(
        query="query",
        law_firm_id=mock_user.law_firm_id,
        user=mock_user,
        top_k=3,
        min_similarity=0.75,
    )

    assert len(results) == 3
    assert results[0].score >= results[1].score >= results[2].score
