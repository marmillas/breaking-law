"""
Search router for the legal platform.

Provides hybrid search and quick suggestion endpoints.
All endpoints require authentication and are tenant-scoped.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    get_embedding_client,
    UserContext,
)
from breaking_law.search.search_service import SearchService
from breaking_law.domain.schemas.search import SearchResultOut, SearchResponse, SuggestionsResponse, SearchRequest

router = APIRouter(
    prefix="/search",
    tags=["search"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=SearchResponse)
async def hybrid_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Perform hybrid search across document chunks.

    Combines vector similarity and full-text search using reciprocal
    rank fusion (RRF) for relevance scoring. Results are filtered by
    tenant, ACL, and confidentiality settings.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    embedding_client = get_embedding_client()
    service = SearchService(db, embedding_client)

    results = await service.hybrid_search(
        query=request.query,
        law_firm_id=current_user.law_firm_id,
        user=current_user,
        top_k=request.top_k,
    )

    return SearchResponse(
        results=[
            SearchResultOut(
                document_id=r.document_id,
                document_title=r.document_title,
                chunk_text=r.chunk_text,
                score=r.score,
                matter_id=r.matter_id,
            )
            for r in results
        ]
    )


@router.get("/suggestions", response_model=SuggestionsResponse)
async def search_suggestions(
    q: str = Query(..., min_length=1, description="Search query prefix"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Quick full-text suggestions for autocomplete.

    Returns chunk text snippets matching the query using PostgreSQL
    full-text search only (faster than hybrid search).
    """
    embedding_client = get_embedding_client()
    service = SearchService(db, embedding_client)

    suggestions = await service.quick_suggestions(
        query=q,
        law_firm_id=current_user.law_firm_id,
        user=current_user,
        limit=limit,
    )

    return SuggestionsResponse(suggestions=suggestions)
