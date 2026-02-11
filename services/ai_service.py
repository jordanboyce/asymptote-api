"""AI enhancement service supporting Anthropic and OpenAI providers.

Provides optional AI-powered search enhancements:
- Result reranking: reorder results by actual relevance using LLM judgment
- Result synthesis: generate a coherent answer with citations from top results

Users provide their own API keys. Keys are never stored server-side.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int, model: str) -> dict:
        """Send a prompt and return {'text': str, 'usage': {'input_tokens': int, 'output_tokens': int, 'model': str}}."""

    @abstractmethod
    def validate(self) -> bool:
        """Check if the API key is valid."""


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    FAST_MODEL = "claude-haiku-4-5-20251001"
    QUALITY_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str, max_tokens: int, model: str) -> dict:
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "text": response.content[0].text.strip(),
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": model,
            },
        }

    def validate(self) -> bool:
        import anthropic
        try:
            self.client.messages.create(
                model=self.FAST_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except anthropic.AuthenticationError:
            logger.warning("Anthropic authentication failed")
            return False
        except anthropic.RateLimitError as e:
            # Quota/billing issues mean the key is valid but account has no credits
            logger.warning(f"Anthropic key valid but quota/rate limit: {e}")
            return True  # Key is valid, just no credits or rate limited
        except Exception as e:
            logger.error(f"Anthropic validation error: {e}")
            raise


class OpenAIProvider(AIProvider):
    """OpenAI provider."""

    FAST_MODEL = "gpt-4o-mini"
    QUALITY_MODEL = "gpt-4o"

    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    def complete(self, prompt: str, max_tokens: int, model: str) -> dict:
        response = self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "text": response.choices[0].message.content.strip(),
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "model": model,
            },
        }

    def validate(self) -> bool:
        from openai import AuthenticationError, RateLimitError
        try:
            self.client.chat.completions.create(
                model=self.FAST_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except AuthenticationError:
            logger.warning("OpenAI authentication failed")
            return False
        except RateLimitError as e:
            # Quota/billing issues mean the key is valid but account has no credits
            # Check if it's a quota error vs rate limit
            error_message = str(e)
            if "quota" in error_message.lower() or "insufficient_quota" in error_message.lower():
                logger.warning(f"OpenAI key valid but quota exceeded: {e}")
                return True  # Key is valid, just no credits
            else:
                logger.warning(f"OpenAI rate limit: {e}")
                return True  # Key is valid, just rate limited
        except Exception as e:
            logger.error(f"OpenAI validation error: {e}")
            raise


def create_provider(provider_name: str, api_key: str) -> AIProvider:
    """Create an AI provider instance."""
    if provider_name == "anthropic":
        return AnthropicProvider(api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


class AIService:
    """Provider-agnostic AI service for search enhancements."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    @property
    def fast_model(self) -> str:
        return self.provider.FAST_MODEL

    @property
    def quality_model(self) -> str:
        return self.provider.QUALITY_MODEL

    def rerank_results(
        self, query: str, results: List[dict], top_k: int
    ) -> dict:
        """Rerank search results by true relevance to the query.

        This is where AI adds genuine value over cosine similarity:
        vectors measure semantic nearness, but an LLM can judge whether
        a chunk actually answers the question.
        """
        if not results:
            return {"reranked_indices": [], "usage": None}

        snippets = []
        for r in results:
            snippets.append(f"[{r['index']}] (file: {r['filename']}) {r['text_snippet'][:200]}")
        snippet_text = "\n\n".join(snippets)

        prompt = (
            "You are a search result reranking assistant. Given a query and numbered "
            "search results, return the indices of the most relevant results ordered "
            "from most to least relevant.\n\n"
            "Rules:\n"
            "- Return ONLY a JSON array of index numbers, e.g. [3, 1, 7, 2]\n"
            f"- Return at most {top_k} indices\n"
            "- Rank by actual relevance to the query, not just keyword overlap\n"
            "- Exclude results that are not relevant at all\n\n"
            f"Query: {query}\n\n"
            f"Results:\n{snippet_text}"
        )

        start = time.time()
        response = self.provider.complete(prompt, max_tokens=300, model=self.fast_model)
        elapsed = time.time() - start

        raw = response["text"]
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            indices = json.loads(raw)
            if not isinstance(indices, list):
                raise ValueError("Expected a JSON array")
            indices = [int(i) for i in indices]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse rerank response: {e}. Using original order.")
            indices = [r["index"] for r in results[:top_k]]

        logger.info(f"Reranked {len(results)} results in {elapsed:.2f}s -> top {len(indices)}")

        return {
            "reranked_indices": indices,
            "usage": response["usage"],
        }

    def synthesize_results(self, query: str, results: List[dict]) -> dict:
        """Generate a coherent answer from search results with citations.

        This is the highest-value AI feature: it turns "here are 10 document
        chunks" into "here is the answer to your question, with sources."
        """
        if not results:
            return {"synthesis": "", "usage": None}

        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(
                f"[Source {i + 1}: {r['filename']}, page {r['page_number']}]\n"
                f"{r['text_snippet']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        prompt = (
            "You are a research assistant. Based on the search results below, "
            "provide a clear, concise answer to the user's query. Cite your sources "
            "using [Source N] notation.\n\n"
            "Rules:\n"
            "- Only use information from the provided sources\n"
            "- Cite specific sources for each claim using [Source N]\n"
            "- If the sources don't contain enough info, say so\n"
            "- Be concise but thorough\n"
            "- Use plain language\n\n"
            f"Query: {query}\n\n"
            f"Sources:\n{context}"
        )

        start = time.time()
        response = self.provider.complete(prompt, max_tokens=1024, model=self.quality_model)
        elapsed = time.time() - start

        logger.info(f"Synthesized answer in {elapsed:.2f}s ({len(response['text'])} chars)")

        return {
            "synthesis": response["text"],
            "usage": response["usage"],
        }
