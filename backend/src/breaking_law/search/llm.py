"""
LLM integration for the legal platform.

Provides an abstract LLM router with OpenAI and stub implementations.
The stub client is for development and testing ONLY.

.. warning::
   PRODUCTION REQUIREMENT: A valid LLM API key is required for production use.
   The `OpenAILLMClient` calls the external LLM API and will fail without a valid key.
   The `StubLLMClient` is for development and testing ONLY — it returns deterministic
   echo responses that contain no real legal reasoning.
   Configure `LLM_PROVIDER=openai` and set `LLM_API_KEY` in production.

.. warning::
   COST CONSIDERATION: Model selection directly affects API cost. GPT-4o-mini
   is the default for cost-efficiency; GPT-4o or larger models increase cost
   significantly but may improve complex legal reasoning quality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Response from an LLM client."""

    content: str
    model: str
    tokens_used: int
    finish_reason: str


class LLMRouter(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The user prompt with context and query.
            system_prompt: The system-level instructions.

        Returns:
            LLMResponse with content and metadata.
        """
        raise NotImplementedError


class OpenAILLMClient(LLMRouter):
    """Production LLM client using OpenAI's chat completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> LLMResponse:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "unknown",
        )


class StubLLMClient(LLMRouter):
    """
    Deterministic stub LLM client for testing and development.

    Returns an echo response that includes the query and a count of
    context sources. This client does NOT call any external API.
    """

    def __init__(self, model: str = "stub"):
        self.model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> LLMResponse:
        # Extract the query from the prompt (everything after "USER QUERY:\n")
        query = ""
        if "USER QUERY:\n" in prompt:
            query = prompt.split("USER QUERY:\n")[-1].split("\n\nANSWER:")[0].strip()

        # Count context sources
        source_count = prompt.count("--- SOURCE")

        content = (
            f"[STUB RESPONSE] Query: '{query}'. "
            f"Retrieved {source_count} source(s). "
            f"System prompt length: {len(system_prompt)} chars."
        )

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=len(prompt.split()),
            finish_reason="stop",
        )


def get_llm_client(config) -> LLMRouter:
    """
    Factory that returns the appropriate LLM client based on configuration.

    Args:
        config: Application configuration object with LLM settings.

    Returns:
        LLMRouter implementation.
    """
    if config.LLM_PROVIDER == "openai":
        return OpenAILLMClient(
            api_key=config.LLM_API_KEY or "",
            model=config.LLM_MODEL,
        )
    return StubLLMClient(model="stub")
