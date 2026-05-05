"""
Tests for the citation validator.
"""

import uuid

import pytest

from breaking_law.search.citation import CitationValidator
from breaking_law.domain.schemas.search import RetrievalResult


@pytest.fixture
def validator():
    return CitationValidator()


@pytest.fixture
def sample_sources():
    doc_id = uuid.uuid4()
    return [
        RetrievalResult(
            chunk_text="Article 1254 of the Civil Code states that contracts are binding.",
            document_id=doc_id,
            document_title="Civil Code",
            matter_id=None,
            score=0.90,
            source_type="document",
        ),
        RetrievalResult(
            chunk_text="The Supreme Court ruling STS 123/2020 confirms this interpretation.",
            document_id=doc_id,
            document_title="Case Law DB",
            matter_id=None,
            score=0.85,
            source_type="document",
        ),
    ]


def test_validate_citations_detects_valid_citations(validator, sample_sources):
    """Citations present in sources are validated."""
    response = (
        "According to Article 1254 of the Civil Code, contracts are binding. "
        "The Supreme Court ruling STS 123/2020 confirms this."
    )
    report = validator.validate_citations(response, sample_sources)

    assert len(report.validated) >= 1
    assert report.confidence_score == 1.0
    assert not report.has_unverified


def test_validate_citations_detects_unverified_citations(validator, sample_sources):
    """Citations not in sources are flagged as unverified."""
    response = (
        "Article 9999 of the Unknown Law applies here. "
        "Also, STS 999/2099 says something relevant."
    )
    report = validator.validate_citations(response, sample_sources)

    assert len(report.unverified) >= 2
    assert report.has_unverified
    assert len(report.validated) == 0
    assert report.confidence_score == 0.0


def test_validate_citations_mixed_valid_and_unverified(validator, sample_sources):
    """Mix of valid and unverified citations produces partial confidence."""
    response = (
        "Article 1254 of the Civil Code is relevant. "
        "Additionally, Article 8888 of a nonexistent law applies."
    )
    report = validator.validate_citations(response, sample_sources)

    assert len(report.validated) >= 1
    assert len(report.unverified) >= 1
    assert report.has_unverified
    assert 0.0 < report.confidence_score < 1.0


def test_validate_citations_no_citations(validator, sample_sources):
    """Text with no citations returns full confidence."""
    response = "This is a general statement with no legal references."
    report = validator.validate_citations(response, sample_sources)

    assert report.validated == []
    assert report.unverified == []
    assert not report.has_unverified
    assert report.confidence_score == 1.0


def test_validate_citations_empty_sources(validator):
    """Validation against empty sources flags all citations."""
    response = "Article 1254 of the Civil Code applies."
    report = validator.validate_citations(response, [])

    assert len(report.unverified) == 1
    assert report.has_unverified
    assert report.confidence_score == 0.0


def test_validate_citations_confidence_score_calculation(validator, sample_sources):
    """Confidence score equals validated / total citations."""
    response = (
        "Article 1254 of the Civil Code applies. "
        "Article 8888 does not. "
        "Article 9999 also does not."
    )
    report = validator.validate_citations(response, sample_sources)
    total = len(report.validated) + len(report.unverified)
    assert total > 0
    expected = len(report.validated) / total
    assert report.confidence_score == pytest.approx(expected, rel=1e-6)


def test_extract_citations_finds_article_references(validator):
    """Regex extracts article references correctly."""
    text = "See art. 123, artículo 456 and arts. 789 y 012."
    citations = validator._extract_citations(text)
    assert any("art. 123" in c.lower() for c in citations)
    assert any("artículo 456" in c.lower() for c in citations)


def test_extract_citations_finds_law_names(validator):
    """Regex extracts law name references."""
    text = "Under Ley 24/1988 and the Código Civil."
    citations = validator._extract_citations(text)
    assert any("Ley 24/1988" in c for c in citations)
    assert any("Código Civil" in c for c in citations)


def test_extract_citations_finds_case_references(validator):
    """Regex extracts case law references."""
    text = "The STS 123/2020 and SAP Barcelona 45/2021 rulings."
    citations = validator._extract_citations(text)
    assert any("STS 123/2020" in c for c in citations)
    assert any("SAP Barcelona 45/2021" in c for c in citations)


def test_fuzzy_match_direct_containment(validator):
    """Direct text containment gives perfect score."""
    score = validator._fuzzy_match("Article 1254", "Article 1254 of the Civil Code")
    assert score == 1.0


def test_fuzzy_match_partial_overlap(validator):
    """Partial overlap gives intermediate score."""
    score = validator._fuzzy_match("Civil Code article", "The Civil Code states")
    assert 0.0 < score < 1.0


def test_fuzzy_match_no_overlap(validator):
    """No overlap gives zero score."""
    score = validator._fuzzy_match("zzzzzz", "The Civil Code states")
    assert score == 0.0
