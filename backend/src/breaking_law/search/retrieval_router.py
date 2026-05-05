"""
Retrieval router for the legal platform.

Provides endpoints to retrieve relevant legal document chunks
with source attribution for a given query.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    get_embedding_client,
    UserContext,
)
from breaking_law.search.search_service import SearchService
from breaking_law.search.retrieval_service import RetrievalService
from breaking_law.domain.schemas.search import RetrievalRequest, RetrievalResultOut, RetrievalResponse

router = APIRouter(
    prefix="/retrieval",
    tags=["retrieval"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/context", response_model=RetrievalResponse)
async def retrieve_context(
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Retrieve relevant legal context for a query.

    Returns document chunks with source attribution, filtered by
    tenant isolation, ACL, confidentiality, and similarity threshold.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    embedding_client = get_embedding_client()
    search_service = SearchService(db, embedding_client)
    retrieval_service = RetrievalService(search_service)

    results = await retrieval_service.retrieve_context_for_user(
        query=request.query,
        law_firm_id=current_user.law_firm_id,
        user=current_user,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
    )

    return RetrievalResponse(
        results=[
            RetrievalResultOut(
                chunk_text=r.chunk_text,
                document_id=r.document_id,
                document_title=r.document_title,
                matter_id=r.matter_id,
                score=r.score,
                source_type=r.source_type,
            )
            for r in results
        ]
    )
