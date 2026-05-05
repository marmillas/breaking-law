"""
Search service for the legal platform.

Provides hybrid search combining vector similarity and PostgreSQL full-text
search with reciprocal rank fusion (RRF) for relevance ranking.
"""

import uuid
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from sqlalchemy import select, text, func, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.shared.embeddings import EmbeddingClient, FullTextSearch
from breaking_law.infra.models import DocumentChunk, Document, DocumentACL, AccessLevel
from breaking_law.api.deps import UserContext


@dataclass
class SearchResult:
    """Single hybrid search result with metadata and fused score."""

    document_id: uuid.UUID
    document_title: str
    chunk_text: str
    score: float
    matter_id: Optional[uuid.UUID]


class SearchService:
    """
    Hybrid search service combining vector similarity and full-text search.

    Uses reciprocal rank fusion (RRF) to merge results from both search
    modalities. RRF parameter k is fixed at 60 per design.
    """

    RRF_K = 60

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_client: EmbeddingClient,
    ):
        self.db = db_session
        self.embedding_client = embedding_client

    async def hybrid_search(
        self,
        query: str,
        law_firm_id: uuid.UUID,
        user: UserContext,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Execute hybrid search across document chunks.

        Args:
            query: User search query string.
            law_firm_id: Tenant ID for isolation.
            user: Authenticated user context for ACL enforcement.
            top_k: Maximum number of results to return.

        Returns:
            List of SearchResult ordered by fused RRF score (descending).
        """
        # Generate query embedding
        query_embeddings = await self.embedding_client.embed([query])
        query_embedding = query_embeddings[0]

        # Run vector search
        vector_results = await self._vector_search(
            query_embedding, law_firm_id, user, top_k * 2
        )

        # Run full-text search
        text_results = await self._full_text_search(
            query, law_firm_id, user, top_k * 2
        )

        # Merge using reciprocal rank fusion
        fused = self._rrf_merge(vector_results, text_results, top_k)
        return fused

    async def _vector_search(
        self,
        query_embedding: List[float],
        law_firm_id: uuid.UUID,
        user: UserContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using cosine distance.

        Returns ranked list of chunk dicts with 'rank' and 'chunk' keys.
        """
        # Build ACL filter subquery
        acl_filter = self._build_acl_filter(user)

        stmt = (
            select(
                DocumentChunk,
                func.cosine_distance(DocumentChunk.embedding, query_embedding).label(
                    "distance"
                ),
            )
            .join(Document)
            .where(
                DocumentChunk.law_firm_id == law_firm_id,
                DocumentChunk.embedding.is_not(None),
                acl_filter,
            )
            .order_by(text("distance"))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "chunk": row[0],
                "document": row[0].version.document if row[0].version else None,
                "rank": idx + 1,
            }
            for idx, row in enumerate(rows)
        ]

    async def _full_text_search(
        self,
        query: str,
        law_firm_id: uuid.UUID,
        user: UserContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        PostgreSQL full-text search using tsvector.

        Returns ranked list of chunk dicts with 'rank' and 'chunk' keys.
        """
        # Build ACL filter subquery
        acl_filter = self._build_acl_filter(user)

        tsquery = FullTextSearch.build_tsquery(query)
        rank_expr = FullTextSearch.rank_results(
            "document_chunks.search_vector", tsquery
        )

        stmt = (
            select(
                DocumentChunk,
                text(rank_expr).label("rank"),
            )
            .join(Document)
            .where(
                DocumentChunk.law_firm_id == law_firm_id,
                DocumentChunk.search_vector.is_not(None),
                text(
                    f"document_chunks.search_vector @@ {tsquery}"
                ),
                acl_filter,
            )
            .order_by(text("rank DESC"))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "chunk": row[0],
                "document": row[0].version.document if row[0].version else None,
                "rank": idx + 1,
            }
            for idx, row in enumerate(rows)
        ]

    def _build_acl_filter(self, user: UserContext):
        """
        Build a SQLAlchemy WHERE clause for ACL and confidentiality filtering.

        Users see:
        - Documents they own
        - Non-confidential documents in their firm
        - Confidential documents where they have explicit access
        """
        # Owner sees everything
        owner_clause = Document.owner_user_id == user.user_id

        # Non-confidential documents visible to firm members
        non_confidential = Document.is_confidential.is_(False)

        # Explicit ACL access
        acl_subquery = exists().where(
            DocumentACL.document_id == Document.id,
            or_(
                DocumentACL.user_id == user.user_id,
                DocumentACL.role == user.role,
            ),
        )

        return or_(owner_clause, non_confidential, acl_subquery)

    def _rrf_merge(
        self,
        vector_results: List[Dict[str, Any]],
        text_results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Merge vector and full-text results using reciprocal rank fusion.

        Score = 1/(k + rank_vector) + 1/(k + rank_text)
        """
        scores: Dict[uuid.UUID, float] = {}
        metadata: Dict[uuid.UUID, Dict[str, Any]] = {}

        for item in vector_results:
            chunk = item["chunk"]
            doc = item["document"]
            rank = item["rank"]
            chunk_id = chunk.id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self.RRF_K + rank)
            metadata[chunk_id] = {
                "document_id": doc.id if doc else None,
                "document_title": doc.title if doc else "",
                "chunk_text": chunk.text_content,
                "matter_id": doc.matter_id if doc else None,
            }

        for item in text_results:
            chunk = item["chunk"]
            doc = item["document"]
            rank = item["rank"]
            chunk_id = chunk.id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self.RRF_K + rank)
            if chunk_id not in metadata:
                metadata[chunk_id] = {
                    "document_id": doc.id if doc else None,
                    "document_title": doc.title if doc else "",
                    "chunk_text": chunk.text_content,
                    "matter_id": doc.matter_id if doc else None,
                }

        # Sort by score descending
        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        results = []
        for chunk_id in sorted_ids[:top_k]:
            meta = metadata[chunk_id]
            results.append(
                SearchResult(
                    document_id=meta["document_id"],
                    document_title=meta["document_title"],
                    chunk_text=meta["chunk_text"],
                    score=scores[chunk_id],
                    matter_id=meta["matter_id"],
                )
            )

        return results

    async def quick_suggestions(
        self,
        query: str,
        law_firm_id: uuid.UUID,
        user: UserContext,
        limit: int = 5,
    ) -> List[str]:
        """
        Fast full-text-only suggestions for autocomplete.

        Args:
            query: Partial query string.
            law_firm_id: Tenant ID.
            user: Authenticated user context.
            limit: Maximum suggestions.

        Returns:
            List of distinct chunk text snippets.
        """
        acl_filter = self._build_acl_filter(user)
        tsquery = FullTextSearch.build_tsquery(query)

        stmt = (
            select(DocumentChunk.text_content)
            .join(Document)
            .where(
                DocumentChunk.law_firm_id == law_firm_id,
                DocumentChunk.search_vector.is_not(None),
                text(f"document_chunks.search_vector @@ {tsquery}"),
                acl_filter,
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return list(rows)
