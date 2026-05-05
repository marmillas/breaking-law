"""
RAG router for the legal platform.

Provides the main RAG endpoint for legal question answering
with source attribution and anti-hallucination guardrails.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    get_embedding_client,
    get_llm_client,
    UserContext,
)
from breaking_law.search.search_service import SearchService
from breaking_law.search.retrieval_service import RetrievalService
from breaking_law.search.rag_service import RAGService
from breaking_law.domain.schemas.search import (
    RAGQueryRequest,
    SourceAttributionOut,
    CitationReportOut,
    RAGQueryResponse,
)

router = APIRouter(
    prefix="/rag",
    tags=["rag"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Execute the full RAG pipeline for a legal query.

    Retrieves relevant document chunks, generates an LLM response,
    validates citations, and returns the answer with source attribution.

    Task types:
        - draft: Draft legal text
        - review: Review existing text
        - summarize: Summarize legal content
        - checklist: Generate compliance checklist
        - analyze: Analyze legal question (default)
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    if request.task_type not in {"draft", "review", "summarize", "checklist", "analyze"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_type: {request.task_type}",
        )

    embedding_client = get_embedding_client()
    llm_client = get_llm_client()
    search_service = SearchService(db, embedding_client)
    retrieval_service = RetrievalService(search_service)
    rag_service = RAGService(
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )

    result = await rag_service.query(
        query=request.query,
        user=current_user,
        task_type=request.task_type,
    )

    return RAGQueryResponse(
        answer=result.answer,
        sources=[
            SourceAttributionOut(
                document_id=s.document_id,
                document_title=s.document_title,
                chunk_text=s.chunk_text,
                score=s.score,
            )
            for s in result.sources
        ],
        citation_report=CitationReportOut(
            validated=[
                {"text": v.text, "matched_source_index": v.matched_source_index, "confidence": v.confidence}
                for v in result.citation_report.validated
            ],
            unverified=result.citation_report.unverified,
            has_unverified=result.citation_report.has_unverified,
            confidence_score=result.citation_report.confidence_score,
        ),
        needs_review=result.needs_review,
        confidence=result.confidence,
    )
