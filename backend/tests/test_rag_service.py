"""
Tests for the RAG service.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from breaking_law.api.deps import UserContext
from breaking_law.search.llm import LLMResponse, StubLLMClient
from breaking_law.search.retrieval_service import RetrievalService, RetrievalResult
from breaking_law.search.rag_service import RAGService


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
def mock_retrieval_service():
    svc = MagicMock(spec=RetrievalService)
    svc.retrieve_context_for_user = AsyncMock()
    return svc


@pytest.fixture
def sample_retrieved():
    doc_id = uuid.uuid4()
    matter_id = uuid.uuid4()
    return [
        RetrievalResult(
            chunk_text="Article 1254 of the Civil Code governs contracts.",
            document_id=doc_id,
            document_title="Civil Code",
            matter_id=matter_id,
            score=0.90,
            source_type="document",
        ),
    ]


@pytest.mark.asyncio
async def test_rag_pipeline_end_to_end(mock_retrieval_service, mock_user, sample_retrieved):
    """Full RAG pipeline produces a response with sources."""
    mock_retrieval_service.retrieve_context_for_user.return_value = sample_retrieved
    llm_client = StubLLMClient()

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=llm_client,
    )

    result = await rag.query(
        query="What governs contracts?",
        user=mock_user,
        task_type="analyze",
    )

    assert result.answer
    assert len(result.sources) == 1
    assert result.sources[0].document_title == "Civil Code"
    assert result.confidence == 1.0  # stub response has no citations
    assert not result.needs_review


@pytest.mark.asyncio
async def test_rag_fallback_when_no_sources(mock_retrieval_service, mock_user):
    """Empty retrieval triggers fallback response."""
    mock_retrieval_service.retrieve_context_for_user.return_value = []
    llm_client = StubLLMClient()

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=llm_client,
    )

    result = await rag.query(
        query="Unknown topic",
        user=mock_user,
        task_type="analyze",
    )

    assert "Insufficient sources" in result.answer or "A lawyer should verify" in result.answer
    assert result.sources == []
    assert result.needs_review is True
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_rag_needs_review_on_unverified_citations(mock_retrieval_service, mock_user, sample_retrieved):
    """Unverified citations in LLM response set needs_review flag."""
    mock_retrieval_service.retrieve_context_for_user.return_value = sample_retrieved

    # Mock LLM client that returns text with an invented citation
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=LLMResponse(
        content="According to Article 9999 of the Fake Law, this applies.",
        model="mock",
        tokens_used=10,
        finish_reason="stop",
    ))

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=mock_llm,
    )

    result = await rag.query(
        query="What applies here?",
        user=mock_user,
        task_type="analyze",
    )

    assert result.needs_review is True
    assert len(result.citation_report.unverified) >= 1
    assert result.citation_report.confidence_score < 1.0


@pytest.mark.asyncio
async def test_rag_task_types(mock_retrieval_service, mock_user, sample_retrieved):
    """Different task types produce responses with appropriate prompts."""
    mock_retrieval_service.retrieve_context_for_user.return_value = sample_retrieved
    llm_client = StubLLMClient()

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=llm_client,
    )

    for task_type in ["draft", "review", "summarize", "checklist", "analyze"]:
        result = await rag.query(
            query="Test query",
            user=mock_user,
            task_type=task_type,
        )
        assert result.answer
        assert len(result.sources) == 1


@pytest.mark.asyncio
async def test_rag_response_includes_citation_report(mock_retrieval_service, mock_user, sample_retrieved):
    """RAG response always includes a citation report."""
    mock_retrieval_service.retrieve_context_for_user.return_value = sample_retrieved
    llm_client = StubLLMClient()

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=llm_client,
    )

    result = await rag.query(
        query="Explain contracts",
        user=mock_user,
        task_type="analyze",
    )

    assert result.citation_report is not None
    assert isinstance(result.citation_report.validated, list)
    assert isinstance(result.citation_report.unverified, list)
    assert isinstance(result.citation_report.has_unverified, bool)
    assert isinstance(result.citation_report.confidence_score, float)


@pytest.mark.asyncio
async def test_rag_query_passes_correct_top_k(mock_retrieval_service, mock_user, sample_retrieved):
    """RAG service passes correct parameters to retrieval."""
    mock_retrieval_service.retrieve_context_for_user.return_value = sample_retrieved
    llm_client = StubLLMClient()

    rag = RAGService(
        retrieval_service=mock_retrieval_service,
        llm_client=llm_client,
    )

    await rag.query(
        query="Test",
        user=mock_user,
        task_type="analyze",
    )

    call_kwargs = mock_retrieval_service.retrieve_context_for_user.call_args.kwargs
    assert call_kwargs["top_k"] == 5
    assert call_kwargs["min_similarity"] == 0.75
    assert call_kwargs["law_firm_id"] == mock_user.law_firm_id
