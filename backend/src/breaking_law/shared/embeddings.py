"""
Document search and indexing infrastructure for legal platform.

Provides text chunking, embedding generation, and full-text search
utilities for building semantic and hybrid search over document contents.

.. warning::
   DEPLOYMENT RISK: The pgvector extension must be enabled in PostgreSQL before migrations run (`CREATE EXTENSION vector;`).
   Required: PostgreSQL with pgvector installed and the extension created in the target database.
   Impact if missing: Migrations will fail when creating the DocumentChunk table; on SQLite (tests) the embedding column falls back to JSON, but production queries using vector similarity will error.

.. warning::
   PRODUCTION REQUIREMENT: A valid embedding API key is required for production use.
   The `OpenAIEmbeddingClient` calls the OpenAI API and will fail without a valid key.
   The `StubEmbeddingClient` is for development and testing ONLY — it produces
   deterministic pseudo-embeddings that are not semantically meaningful.
   Configure `EMBEDDING_PROVIDER=openai` and set `EMBEDDING_API_KEY` in production.
"""

import hashlib
import math
import time
from abc import ABC, abstractmethod
from typing import List

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200
DEFAULT_EMBEDDING_DIMENSIONS = 1536


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for indexing.

    Args:
        text: Source text to split.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


class EmbeddingClient(ABC):
    """Abstract base class for embedding model clients."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a list of texts.

        Args:
            texts: List of input strings to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        raise NotImplementedError


class StubEmbeddingClient(EmbeddingClient):
    """
    Deterministic pseudo-embedding client for testing and development.

    Generates pseudo-random vectors from a hash of the input text.
    Vectors are normalized to unit length so cosine similarity works.
    This client does NOT call any external API.
    """

    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS):
        self.dimensions = dimensions

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def _hash_to_vector(self, text: str) -> List[float]:
        """Generate a deterministic normalized vector from text hash."""
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(self.dimensions):
            # Expand hash bytes deterministically
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Map to [-1, 1]
            val = (byte_val / 255.0) * 2 - 1
            vector.append(val)
        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


class OpenAIEmbeddingClient(EmbeddingClient):
    """
    Production embedding client using OpenAI's text-embedding API.

    Supports batch processing and exponential backoff retry logic.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        client = self._get_client()
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = await self._embed_batch_with_retry(client, batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch_with_retry(
        self, client, batch: List[str]
    ) -> List[List[float]]:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await client.embeddings.create(
                    input=batch,
                    model=self.model,
                    dimensions=self.dimensions,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:
                last_exception = exc
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    time.sleep(wait)
                else:
                    break
        raise RuntimeError(
            f"OpenAI embedding API failed after {self.max_retries} attempts"
        ) from last_exception


def get_embedding_client(config) -> EmbeddingClient:
    """
    Factory that returns the appropriate embedding client based on config.

    Args:
        config: Application configuration object with embedding settings.

    Returns:
        EmbeddingClient implementation.
    """
    if config.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingClient(
            api_key=config.EMBEDDING_API_KEY or "",
            model=config.EMBEDDING_MODEL,
            dimensions=config.EMBEDDING_DIMENSIONS,
            batch_size=config.EMBEDDING_BATCH_SIZE,
        )
    return StubEmbeddingClient(dimensions=config.EMBEDDING_DIMENSIONS)


class FullTextSearch:
    """
    PostgreSQL full-text search SQL generator.

    These methods return SQL fragment strings suitable for use with
    SQLAlchemy's `text()` construct. They assume the 'spanish' text
    search configuration is installed in PostgreSQL.
    """

    @staticmethod
    def build_tsvector(text: str) -> str:
        """
        Generate a tsvector SQL expression for the given text.

        Args:
            text: Raw text or column reference to vectorize.

        Returns:
            SQL fragment string.
        """
        return f"to_tsvector('spanish', {text})"

    @staticmethod
    def build_tsquery(query: str, exact_phrase: bool = False) -> str:
        """
        Generate a tsquery SQL expression for the given query string.

        Args:
            query: User search query.
            exact_phrase: If True, use phraseto_tsquery for exact phrase matching.

        Returns:
            SQL fragment string.
        """
        if exact_phrase:
            return f"phraseto_tsquery('spanish', '{query}')"
        return f"plainto_tsquery('spanish', '{query}')"

    @staticmethod
    def rank_results(tsvector_col: str, tsquery: str) -> str:
        """
        Generate a ts_rank SQL expression for relevance scoring.

        Args:
            tsvector_col: tsvector column name or expression.
            tsquery: tsquery expression string.

        Returns:
            SQL fragment string.
        """
        return f"ts_rank({tsvector_col}, {tsquery})"
