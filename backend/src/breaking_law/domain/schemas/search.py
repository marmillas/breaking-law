"""
Search schemas for hybrid search, retrieval, and RAG.
"""

import uuid
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


@dataclass
class RetrievalResult:
    """A retrieved document chunk with full metadata for citation."""

    chunk_text: str
    document_id: uuid.UUID
    document_title: str
    matter_id: Optional[uuid.UUID]
    score: float
    source_type: str


class SearchResultOut(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_text: str
    score: float
    matter_id: Optional[uuid.UUID]


class SearchResponse(BaseModel):
    results: List[SearchResultOut]


class SuggestionsResponse(BaseModel):
    suggestions: List[str]


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    min_similarity: float = 0.75


class RetrievalResultOut(BaseModel):
    chunk_text: str
    document_id: uuid.UUID
    document_title: str
    matter_id: Optional[uuid.UUID]
    score: float
    source_type: str


class RetrievalResponse(BaseModel):
    results: List[RetrievalResultOut]


class RAGQueryRequest(BaseModel):
    query: str
    task_type: str = "analyze"


class SourceAttributionOut(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_text: str
    score: float


class CitationReportOut(BaseModel):
    validated: List[dict]
    unverified: List[str]
    has_unverified: bool
    confidence_score: float


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[SourceAttributionOut]
    citation_report: CitationReportOut
    needs_review: bool
    confidence: float
