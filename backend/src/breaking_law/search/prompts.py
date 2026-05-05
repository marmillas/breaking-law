"""
Prompt management system for the legal AI platform.

Provides base system prompts with anti-hallucination guardrails and
prompt builders for different legal task types.
"""

from typing import List

from breaking_law.domain.schemas.search import RetrievalResult


LEGAL_SYSTEM_PROMPT = """\
You are a legal AI assistant specialized in Spanish civil and commercial law.

CRITICAL RULES — VIOLATING THESE IS A MALPRACTICE RISK:
1. ONLY cite legislation, jurisprudence, or legal sources that appear in the
   provided context documents. Never cite laws from memory.
2. If the provided context does not contain sufficient information to answer
   with confidence, you MUST respond: "The available sources do not contain
   sufficient information to answer this question. A lawyer should verify
   this point manually."
3. Never invent case law, article numbers, or legal interpretations.
4. Always indicate the source document and chunk for every citation.
5. When drafting legal text, mark AI-generated sections clearly so the
   lawyer can review before signing.
6. Respect confidentiality markings on documents.
"""

TASK_INSTRUCTIONS = {
    "draft": (
        "TASK: Draft legal text based on the user's request.\n"
        "- Produce clear, professional legal language appropriate for Spanish civil/commercial law.\n"
        "- Mark every AI-generated section with [AI-DRAFT] so the lawyer can review before signing.\n"
        "- Reference the provided context documents for legal basis.\n"
        "- If the context is insufficient, state so explicitly instead of inventing content."
    ),
    "review": (
        "TASK: Review the provided legal text for accuracy, completeness, and compliance.\n"
        "- Identify any clauses that contradict the provided legal sources.\n"
        "- Flag missing mandatory provisions based on the context documents.\n"
        "- Suggest improvements with references to specific source documents.\n"
        "- If the context is insufficient to fully review, state which areas need manual verification."
    ),
    "summarize": (
        "TASK: Summarize the legal content requested by the user.\n"
        "- Provide a concise but accurate summary of the relevant legal points.\n"
        "- Include key citations with source document references.\n"
        "- Do not add information not present in the context documents.\n"
        "- If the context is insufficient, state that no summary can be provided."
    ),
    "checklist": (
        "TASK: Generate a compliance checklist based on the user's request.\n"
        "- List each item with the legal basis from the provided context documents.\n"
        "- Indicate which items are mandatory and which are recommended.\n"
        "- If the context does not cover a required checklist area, flag it for manual verification."
    ),
    "analyze": (
        "TASK: Analyze the legal question or scenario posed by the user.\n"
        "- Provide a structured analysis based solely on the provided context documents.\n"
        "- Cite specific articles, laws, or jurisprudence found in the context.\n"
        "- Identify risks, obligations, and rights as supported by the sources.\n"
        "- If the context is insufficient, clearly state which aspects require lawyer verification."
    ),
}


def build_prompt(
    query: str,
    context: List[RetrievalResult],
    task_type: str,
) -> str:
    """
    Build the full prompt with retrieved context inlined.

    Args:
        query: User's natural language query.
        context: List of retrieved document chunks with metadata.
        task_type: One of draft, review, summarize, checklist, analyze.

    Returns:
        The complete prompt string ready for the LLM.
    """
    task_instructions = TASK_INSTRUCTIONS.get(
        task_type, TASK_INSTRUCTIONS["analyze"]
    )

    context_blocks = []
    for idx, result in enumerate(context, start=1):
        matter_info = f"Matter: {result.matter_id}\n" if result.matter_id else ""
        block = (
            f"--- SOURCE {idx} ---\n"
            f"Document: {result.document_title}\n"
            f"Type: {result.source_type}\n"
            f"{matter_info}"
            f"Relevance Score: {result.score:.4f}\n"
            f"\n{result.chunk_text}\n"
        )
        context_blocks.append(block)

    context_section = "\n".join(context_blocks) if context_blocks else "No relevant sources were found in the knowledge base."

    prompt = (
        f"{task_instructions}\n\n"
        f"CONTEXT DOCUMENTS:\n"
        f"{context_section}\n\n"
        f"USER QUERY:\n{query}\n\n"
        f"ANSWER:"
    )

    return prompt
