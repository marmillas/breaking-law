"""
RAG (Retrieval-Augmented Generation) service for the legal platform.

Orchestrates the full pipeline: retrieve context, build prompt,
call LLM, validate citations, and build the final response.
"""

import uuid
from dataclasses import dataclass
from typing import List, Optional

from breaking_law.api.deps import UserContext
from breaking_law.search.llm import LLMRouter, LLMResponse
from breaking_law.search.prompts import LEGAL_SYSTEM_PROMPT, build_prompt
from breaking_law.search.retrieval_service import RetrievalService
from breaking_law.domain.schemas.search import RetrievalResult
from breaking_law.search.citation import CitationValidator, CitationReport


@dataclass
class SourceAttribution:
    """Attribution for a source used in the RAG response."""

    document_id: uuid.UUID
    document_title: str
    chunk_text: str
    score: float


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""

    answer: str
    sources: List[SourceAttribution]
    citation_report: CitationReport
    needs_review: bool
    confidence: float


class RAGService:
    """
    Orchestrates the full RAG pipeline with anti-hallucination guardrails.

    Flow:
        1. Retrieve relevant document chunks via RetrievalService.
        2. Build a legal prompt with inlined context.
        3. Generate response via LLM.
        4. Validate citations against retrieved sources.
        5. Build final response with confidence and review flags.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: LLMRouter,
        citation_validator: Optional[CitationValidator] = None,
    ):
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client
        self.citation_validator = citation_validator or CitationValidator()

    async def query(
        self,
        query: str,
        user: UserContext,
        task_type: str = "analyze",
    ) -> RAGResponse:
        """
        Execute the full RAG pipeline for a user query.

        Args:
            query: User's natural language query.
            user: Authenticated user context for ACL and tenant isolation.
            task_type: One of draft, review, summarize, checklist, analyze.

        Returns:
            RAGResponse with answer, sources, citation report, and confidence.
        """
        # Step 1: Retrieve context
        retrieved = await self.retrieval_service.retrieve_context_for_user(
            query=query,
            law_firm_id=user.law_firm_id,
            user=user,
            top_k=5,
            min_similarity=0.75,
        )

        # Fallback when no sources pass the threshold
        if not retrieved:
            return RAGResponse(
                answer=(
                    "The available sources do not contain sufficient information "
                    "to answer this question. A lawyer should verify this point manually."
                ),
                sources=[],
                citation_report=CitationReport(
                    validated=[],
                    unverified=[],
                    has_unverified=False,
                    confidence_score=0.0,
                ),
                needs_review=True,
                confidence=0.0,
            )

        # Step 2: Build prompt
        prompt = build_prompt(
            query=query,
            context=retrieved,
            task_type=task_type,
        )

        # Step 3: Call LLM
        llm_response: LLMResponse = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=LEGAL_SYSTEM_PROMPT,
        )

        # Step 4: Validate citations
        citation_report = self.citation_validator.validate_citations(
            response=llm_response.content,
            retrieved_sources=retrieved,
        )

        # Step 5: Build response
        needs_review = citation_report.has_unverified
        confidence = citation_report.confidence_score

        sources = [
            SourceAttribution(
                document_id=r.document_id,
                document_title=r.document_title,
                chunk_text=r.chunk_text,
                score=r.score,
            )
            for r in retrieved
        ]

        return RAGResponse(
            answer=llm_response.content,
            sources=sources,
            citation_report=citation_report,
            needs_review=needs_review,
            confidence=confidence,
        )
