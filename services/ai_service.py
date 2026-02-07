"""AI enhancement service using Anthropic Claude API.

Provides optional AI-powered search enhancements:
- Query enhancement: expand queries with synonyms and related terms
- Result reranking: reorder results by actual relevance using LLM judgment
- Result synthesis: generate a coherent answer with citations from top results

All features require a user-provided Anthropic API key and degrade
gracefully if the key is missing or API calls fail.
"""

import json
import logging
import time
from typing import List, Optional

import anthropic

logger = logging.getLogger(__name__)


class AIService:
    """Handles AI-powered search enhancements using user-provided API keys."""

    QUERY_MODEL = "claude-haiku-4-5-20251001"
    RERANK_MODEL = "claude-haiku-4-5-20251001"
    SYNTHESIS_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def validate_key(api_key: str) -> bool:
        """Check whether an API key is valid by making a minimal API call."""
        try:
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model=AIService.QUERY_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except anthropic.AuthenticationError:
            return False

    def enhance_query(self, query: str) -> dict:
        """Expand a search query with synonyms and related terms.

        Returns dict with 'enhanced_query' and 'usage' keys.
        """
        start = time.time()
        response = self.client.messages.create(
            model=self.QUERY_MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a search query expansion assistant. Given a user search query, "
                        "produce an expanded version that includes synonyms, related terms, and "
                        "alternate phrasings that would help find relevant documents.\n\n"
                        "Rules:\n"
                        "- Keep the original query terms\n"
                        "- Add synonyms and closely related terms\n"
                        "- Do NOT add unrelated concepts\n"
                        "- Output ONLY the expanded query text, nothing else\n"
                        "- Keep it under 100 words\n\n"
                        f"Query: {query}"
                    ),
                }
            ],
        )
        enhanced = response.content[0].text.strip()
        elapsed = time.time() - start
        logger.info(f"Query enhanced in {elapsed:.2f}s: '{query}' -> '{enhanced[:80]}...'")

        return {
            "enhanced_query": enhanced,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": self.QUERY_MODEL,
            },
        }

    def rerank_results(
        self, query: str, results: List[dict], top_k: int
    ) -> dict:
        """Rerank search results by true relevance to the query.

        Args:
            query: original user query
            results: list of dicts with 'index', 'filename', 'text_snippet', 'similarity_score'
            top_k: how many results to return after reranking

        Returns dict with 'reranked_indices' and 'usage' keys.
        """
        if not results:
            return {"reranked_indices": [], "usage": None}

        # Build a numbered list of snippets for the LLM
        snippets = []
        for r in results:
            snippets.append(f"[{r['index']}] (file: {r['filename']}) {r['text_snippet'][:200]}")
        snippet_text = "\n\n".join(snippets)

        start = time.time()
        response = self.client.messages.create(
            model=self.RERANK_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
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
                    ),
                }
            ],
        )
        elapsed = time.time() - start

        # Parse the JSON array from the response
        raw = response.content[0].text.strip()
        # Handle possible markdown code blocks
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
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": self.RERANK_MODEL,
            },
        }

    def synthesize_results(self, query: str, results: List[dict]) -> dict:
        """Generate a coherent answer from search results with citations.

        Args:
            query: original user query
            results: list of dicts with 'filename', 'page_number', 'text_snippet'

        Returns dict with 'synthesis' and 'usage' keys.
        """
        if not results:
            return {"synthesis": "", "usage": None}

        # Build context from results
        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(
                f"[Source {i + 1}: {r['filename']}, page {r['page_number']}]\n"
                f"{r['text_snippet']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        start = time.time()
        response = self.client.messages.create(
            model=self.SYNTHESIS_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
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
                    ),
                }
            ],
        )
        elapsed = time.time() - start
        synthesis = response.content[0].text.strip()

        logger.info(f"Synthesized answer in {elapsed:.2f}s ({len(synthesis)} chars)")

        return {
            "synthesis": synthesis,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": self.SYNTHESIS_MODEL,
            },
        }
