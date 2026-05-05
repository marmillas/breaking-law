"""
Tests for the prompt management system.
"""

import uuid

import pytest

from breaking_law.search.prompts import (
    LEGAL_SYSTEM_PROMPT,
    build_prompt,
    TASK_INSTRUCTIONS,
)
from breaking_law.domain.schemas.search import RetrievalResult


@pytest.fixture
def sample_results():
    doc_id = uuid.uuid4()
    matter_id = uuid.uuid4()
    return [
        RetrievalResult(
            chunk_text="Article 1254 of the Civil Code governs contracts.",
            document_id=doc_id,
            document_title="Civil Code Reference",
            matter_id=matter_id,
            score=0.92,
            source_type="document",
        ),
        RetrievalResult(
            chunk_text="Commercial law article 44 applies here.",
            document_id=doc_id,
            document_title="Commercial Law Guide",
            matter_id=None,
            score=0.81,
            source_type="knowledge_base",
        ),
    ]


def test_legal_system_prompt_contains_anti_hallucination_rules():
    """The system prompt includes all anti-hallucination guardrails."""
    assert "ONLY cite legislation" in LEGAL_SYSTEM_PROMPT
    assert "Never cite laws from memory" in LEGAL_SYSTEM_PROMPT
    assert "A lawyer should verify" in LEGAL_SYSTEM_PROMPT
    assert "Never invent case law" in LEGAL_SYSTEM_PROMPT
    assert "source document and chunk" in LEGAL_SYSTEM_PROMPT
    assert "Respect confidentiality" in LEGAL_SYSTEM_PROMPT


def test_build_prompt_includes_task_instructions(sample_results):
    """Prompt includes task-specific instructions."""
    prompt = build_prompt(
        query="Draft a contract clause",
        context=sample_results,
        task_type="draft",
    )
    assert TASK_INSTRUCTIONS["draft"] in prompt
    assert "Draft legal text" in prompt


def test_build_prompt_includes_context_sources(sample_results):
    """Prompt inlines retrieved context sources."""
    prompt = build_prompt(
        query="What governs contracts?",
        context=sample_results,
        task_type="analyze",
    )
    assert "--- SOURCE 1 ---" in prompt
    assert "--- SOURCE 2 ---" in prompt
    assert "Civil Code Reference" in prompt
    assert "Commercial Law Guide" in prompt
    assert "Article 1254" in prompt
    assert "Matter:" in prompt  # matter_id is present on first result


def test_build_prompt_includes_user_query(sample_results):
    """Prompt includes the user query at the end."""
    prompt = build_prompt(
        query="Explain liability",
        context=sample_results,
        task_type="analyze",
    )
    assert "USER QUERY:\nExplain liability" in prompt


def test_build_prompt_handles_empty_context():
    """Prompt handles empty context gracefully."""
    prompt = build_prompt(
        query="What is the law?",
        context=[],
        task_type="summarize",
    )
    assert "No relevant sources were found" in prompt


@pytest.mark.parametrize("task_type", ["draft", "review", "summarize", "checklist", "analyze"])
def test_build_prompt_all_task_types(task_type, sample_results):
    """All task types produce valid prompts with instructions."""
    prompt = build_prompt(
        query="Test query",
        context=sample_results,
        task_type=task_type,
    )
    assert TASK_INSTRUCTIONS[task_type] in prompt
    assert "ANSWER:" in prompt


def test_build_prompt_defaults_to_analyze_for_unknown_task(sample_results):
    """Unknown task types fall back to analyze instructions."""
    prompt = build_prompt(
        query="Test",
        context=sample_results,
        task_type="unknown_task",
    )
    assert TASK_INSTRUCTIONS["analyze"] in prompt
