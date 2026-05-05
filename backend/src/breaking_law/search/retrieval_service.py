"""
Document retrieval engine for the RAG pipeline.

Provides high-confidence retrieval of relevant legal document chunks,
with similarity threshold filtering and source attribution.
"""

import uuid
from typing import List

from breaking_law.search.search_service import SearchService
from breaking_law.api.deps import UserContext
from breaking_law.domain.schemas.search import RetrievalResult


class RetrievalService:
    """
    High-confidence document retrieval service for RAG.

    Wraps hybrid search with similarity threshold filtering and
    enriches results with parent document metadata for source attribution.
    """

    DEFAULT_MIN_SIMILARITY = 0.75

    def __init__(self, search_service: SearchService):
        self.search_service = search_service

    async def retrieve_context(
        self,
        query: str,
        law_firm_id: uuid.UUID,
        top_k: int = 5,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant legal context for a query.

        Args:
            query: User's natural language query.
            law_firm_id: Tenant ID for isolation.
            top_k: Maximum number of results to return.
            min_similarity: Minimum similarity score (0.0-1.0). Results below
                this threshold are discarded to reduce hallucination risk.

        Returns:
            List of RetrievalResult ordered by score descending.
            Empty list if no results pass the threshold (triggers fallback
            behavior in the LLM layer).
        """
        # Use the search service's current_user if available; otherwise pass a minimal context
        # The SearchService.hybrid_search requires a UserContext for ACL filtering.
        # RetrievalService is typically called from RAGService which has the user.
        raise NotImplementedError(
            "Use retrieve_context_for_user() with an explicit UserContext."
        )

    async def retrieve_context_for_user(
        self,
        query: str,
        law_firm_id: uuid.UUID,
        user: UserContext,
        top_k: int = 5,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant legal context for a query with user ACL enforcement.

        Args:
            query: User's natural language query.
            law_firm_id: Tenant ID for isolation.
            user: Authenticated user context for ACL and confidentiality filtering.
            top_k: Maximum number of results to return.
            min_similarity: Minimum similarity score (0.0-1.0).

        Returns:
            List of RetrievalResult ordered by score descending.
            Empty list if no results pass the threshold.
        """
        candidates = await self.search_service.hybrid_search(
            query=query,
            law_firm_id=law_firm_id,
            user=user,
            top_k=top_k * 2,  # Retrieve extra to allow threshold filtering
        )

        results: List[RetrievalResult] = []
        for candidate in candidates:
            if candidate.score >= min_similarity:
                results.append(
                    RetrievalResult(
                        chunk_text=candidate.chunk_text,
                        document_id=candidate.document_id,
                        document_title=candidate.document_title,
                        matter_id=candidate.matter_id,
                        score=candidate.score,
                        source_type="document",
                    )
                )

        # Sort by score descending and limit to top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
