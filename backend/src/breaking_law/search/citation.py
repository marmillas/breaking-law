"""
Citation validator for anti-hallucination guardrails.

Parses LLM responses for legal citations and validates them against
the retrieved sources using fuzzy matching.
"""

import re
from dataclasses import dataclass
from typing import List

from breaking_law.domain.schemas.search import RetrievalResult


@dataclass
class ValidatedCitation:
    """A citation that was found in the retrieved sources."""

    text: str
    matched_source_index: int
    confidence: float


@dataclass
class CitationReport:
    """Report on citation validation for an LLM response."""

    validated: List[ValidatedCitation]
    unverified: List[str]
    has_unverified: bool
    confidence_score: float


class CitationValidator:
    """
    Validates citations in LLM responses against retrieved sources.

    Uses regex-based extraction for article numbers, law names, and case
    references, then performs fuzzy matching against the source chunks.
    """

    # Patterns for common Spanish legal citation formats
    CITATION_PATTERNS = [
        # Article references: "artículo 123", "art. 123", "arts. 123 y 124", "Article 123"
        re.compile(
            r"\b(?:art(?:[íi]culo)?\.?|article|articles)\s*\d+(?:\s*(?:,\s*y\s*|\s*y\s*|,\s*)\d+)*",
            re.IGNORECASE,
        ),
        # Law names: "Ley 24/1988", "Real Decreto 123/2020", "Código Civil", "Unknown Law"
        re.compile(
            r"\b(?:Ley\s+\d+\/\d+|Real\s+Decreto\s+\d+\/\d+|C[oó]digo\s+Civil|C[oó]digo\s+de\s+Comercio|"
            r"Constituci[oó]n\s+Española|Ley\s+Org[aá]nica\s+\d+\/\d+|\w+\s+Law)\b",
            re.IGNORECASE,
        ),
        # Case references: "STS 123/2020", "SAP Barcelona 45/2021"
        re.compile(
            r"\b(?:STS|SSTS|SAP|STSJ)\s+(?:[A-Za-záéíóúÁÉÍÓÚñÑ\s]+\s+)?\d+\/\d{4}\b",
            re.IGNORECASE,
        ),
    ]

    def _extract_citations(self, text: str) -> List[str]:
        """Extract potential citations from text using regex patterns."""
        citations: List[str] = []
        for pattern in self.CITATION_PATTERNS:
            for match in pattern.finditer(text):
                citation = match.group(0)
                if citation not in citations:
                    citations.append(citation)
        return citations

    def _fuzzy_match(self, citation: str, source_text: str) -> float:
        """
        Compute a simple fuzzy match score between a citation and source text.

        Returns a score between 0.0 and 1.0 based on token overlap.
        """
        citation_lower = citation.lower()
        source_lower = source_text.lower()

        # Direct containment is a strong signal
        if citation_lower in source_lower:
            return 1.0

        # Token overlap ratio
        citation_tokens = set(citation_lower.split())
        source_tokens = set(source_lower.split())
        if not citation_tokens:
            return 0.0

        overlap = citation_tokens & source_tokens
        return len(overlap) / len(citation_tokens)

    def validate_citations(
        self,
        response: str,
        retrieved_sources: List[RetrievalResult],
    ) -> CitationReport:
        """
        Validate citations in an LLM response against retrieved sources.

        Args:
            response: The LLM-generated text to validate.
            retrieved_sources: The sources that were provided to the LLM.

        Returns:
            CitationReport with validated and unverified citations.
        """
        citations = self._extract_citations(response)

        validated: List[ValidatedCitation] = []
        unverified: List[str] = []

        for citation in citations:
            best_score = 0.0
            best_index = -1

            for idx, source in enumerate(retrieved_sources):
                score = self._fuzzy_match(citation, source.chunk_text)
                if score > best_score:
                    best_score = score
                    best_index = idx

            # Threshold for considering a citation validated
            if best_score >= 0.6:
                validated.append(
                    ValidatedCitation(
                        text=citation,
                        matched_source_index=best_index,
                        confidence=best_score,
                    )
                )
            else:
                unverified.append(citation)

        has_unverified = len(unverified) > 0

        # Confidence score: ratio of validated citations to total citations
        total = len(citations)
        confidence_score = len(validated) / total if total > 0 else 1.0

        return CitationReport(
            validated=validated,
            unverified=unverified,
            has_unverified=has_unverified,
            confidence_score=confidence_score,
        )
