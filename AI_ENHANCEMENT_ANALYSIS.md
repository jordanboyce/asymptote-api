# AI Enhancement Analysis: Asymptote API

## Executive Summary

After analyzing the Asymptote API codebase, I recommend implementing three AI features in this order:

1. **Query Enhancement** — Low complexity, invisible improvement, near-zero cost
2. **Result Reranking** — Medium complexity, noticeably better precision
3. **Result Synthesis** — Medium-high complexity, transformative user value

These three form a natural pipeline: *Enhanced Query → Better Search → Reranked Results → AI Summary*. Each is independently valuable and degrades gracefully without an API key.

---

## Codebase Assessment

### Architecture Fit: Excellent

The codebase is well-structured for adding optional AI features:

- **Clean pipeline in `services/indexing/indexer.py:101-121`**: The `search()` method has a simple two-step flow (`embed_query` → `vector_store.search`). Pre-search and post-search hooks slot in naturally.
- **Pydantic Settings in `config.py`**: Adding `anthropic_api_key: Optional[str] = None` and feature flags requires minimal changes.
- **Pydantic schemas in `models/schemas.py`**: `SearchRequest` and `SearchResponse` can be extended with optional fields without breaking existing clients.
- **Dependency injection via FastAPI**: The `get_indexer()` pattern in `main.py:46-53` makes it easy to inject an AI service alongside existing services.
- **No authentication layer**: The Anthropic API key can be introduced as a server-side config (`.env`), a per-request header, or both.

### Key Integration Points

| Location | What happens | AI hook opportunity |
|---|---|---|
| `indexer.py:115` | Query embedding generated | **Before**: expand/rewrite query |
| `indexer.py:118` | FAISS vector search | **After**: rerank results |
| `main.py:260` | Results returned to client | **After**: synthesize answer |
| `config.py:7-35` | Settings loaded | **Add**: AI feature flags + API key |
| `models/schemas.py:51-55` | Search request defined | **Add**: optional AI toggle fields |
| `models/schemas.py:58-63` | Search response defined | **Add**: optional synthesis field |

---

## Feature-by-Feature Analysis

### 1. Query Enhancement ⭐ RECOMMENDED — Implement First

**What it does**: Before embedding the user's query, send it to Claude (Haiku) to extract synonyms, related terms, domain-specific jargon, and alternate phrasings. Combine the expanded terms with the original query, then embed the enriched text.

**Concrete example**:
```
User query:    "database optimization"
Enhanced query: "database optimization SQL performance tuning query optimization
                index strategies database indexing slow queries execution plans"
```

**Why it fits this codebase**:

- Single insertion point: `indexer.py:115`, before `embed_query()`. The enhanced query replaces the original for embedding purposes.
- No schema changes needed — the enhancement is invisible to the API consumer.
- The original query is preserved in the response (`SearchResponse.query` stays unchanged).
- If the Anthropic API call fails or no key is configured, the original query passes through unchanged.

**Implementation sketch**:
```
New file:   services/ai_service.py        (~80 lines)
Modified:   services/indexing/indexer.py   (~10 lines changed in search())
Modified:   config.py                      (~5 lines: api_key, enable flag)
New dep:    anthropic                      (in requirements.txt)
```

**Cost per search**: ~100-200 input tokens, ~50-100 output tokens = **$0.00005-0.0001** (Haiku)

**Measurable improvement**: Compare recall@10 with and without enhancement on a test corpus. Enhancement should surface relevant documents that use different terminology than the query.

**Risk**: Low. Worst case is a slightly slower search (~200ms added) that returns the same quality results as before.

---

### 2. Result Reranking ⭐ RECOMMENDED — Implement Second

**What it does**: After FAISS returns cosine similarity results, take the top N results (e.g., 50) and ask Claude to reorder them by actual relevance to the user's question. Return the reranked top_k.

**Why cosine similarity alone isn't enough**: FAISS measures "semantic nearness" between embeddings, but this isn't the same as "answers the user's question." A chunk about "database backup procedures" might be semantically close to "database optimization" but isn't relevant. An LLM understands this distinction.

**Why it fits this codebase**:

- Single insertion point: `indexer.py:118`, after `vector_store.search()` returns.
- Modify `search()` to request more results from FAISS (e.g., `top_k * 5`), then rerank and truncate.
- Result schema stays identical — only the ordering changes.
- If reranking fails, return the original FAISS-ordered results.

**Implementation sketch**:
```
Modified:   services/ai_service.py         (~60 lines added: rerank method)
Modified:   services/indexing/indexer.py    (~15 lines changed in search())
Modified:   models/schemas.py              (~3 lines: optional reranked flag)
```

**Cost per search**: ~500-1000 input tokens (query + 50 snippets of ~100 chars each), ~200 output tokens = **$0.0003-0.0005** (Haiku)

**Measurable improvement**: Compare precision@10 of reranked vs unreranked results. Particularly effective for:
- Ambiguous queries where cosine similarity returns plausible but wrong results
- Specific questions where the best answer is buried in result #15-30
- Large corpora (100k+ docs) where the top-50 FAISS results include many near-misses

**Risk**: Low-Medium. Adds ~500ms-1s latency per search. Mitigated by making it opt-in via request parameter.

---

### 3. Result Synthesis ⭐ RECOMMENDED — Implement Third

**What it does**: After reranking, send the top results to Claude (Sonnet) to generate a coherent answer with citations back to specific documents and pages.

**Concrete example**:
```
User query: "What are the recommended backup retention policies?"

Synthesis:
  "Based on your documents, the recommended backup retention policy is a
   3-2-1 strategy: 3 copies of data, on 2 different media types, with 1
   offsite copy [IT-Policy-2024.pdf, p.12]. Daily incremental backups should
   be retained for 30 days, weekly full backups for 90 days, and monthly
   archives for 7 years [Compliance-Guide.pdf, p.45]. For database-specific
   backups, point-in-time recovery logs should be kept for at least 14 days
   [DBA-Handbook.pdf, p.8]."
```

**Why it fits this codebase**:

- New optional field on `SearchResponse`: `synthesis: Optional[str] = None`
- Activated via request parameter: `SearchRequest.synthesize: bool = False`
- Uses the already-reranked results as input (builds on feature #2)
- The existing `results` array is always returned — synthesis is additive

**Implementation sketch**:
```
Modified:   services/ai_service.py         (~80 lines added: synthesize method)
Modified:   services/indexing/indexer.py    (~10 lines)
Modified:   models/schemas.py              (~5 lines: synthesize flag + response field)
Modified:   main.py                         (~10 lines: pass-through of synthesis)
Frontend:   components/SearchTab.vue        (~30 lines: render synthesis block)
```

**Cost per search**: ~2000-4000 input tokens (query + top 10 full snippets), ~500-1000 output tokens = **$0.01-0.02** (Sonnet for quality)

**Measurable improvement**: User satisfaction — transforms "here are 10 documents" into "here is the answer, sourced from your documents." Particularly valuable for:
- Research tasks across large document sets
- Compliance/policy questions spanning multiple documents
- Any use case where the answer requires synthesizing information from multiple sources

**Risk**: Medium. Requires careful prompt engineering for citation accuracy. Hallucination risk mitigated by grounding the response in actual document text and providing the source results alongside the synthesis.

---

## Features to Defer

### 4. Multi-Hop Search — DEFER

**Why not now**: Requires recursive search logic, state management between iterations, and termination conditions. The orchestration complexity is high relative to the marginal improvement over query enhancement + reranking. Once features 1-3 are stable, multi-hop becomes a natural extension.

**Prerequisite**: Features 1 and 2 (query enhancement provides most of the "find related concepts" value with far less complexity).

### 5. Question Decomposition — DEFER

**Why not now**: Depends on multi-hop infrastructure. Requires parallel search orchestration and result merging logic. The synthesis feature (#3) already handles multi-document answers for straightforward queries.

**Prerequisite**: Features 1, 2, 3, and 4.

### 6. Pre-Processing Intelligence — DEFER

**Why not now**: Modifying the indexing pipeline (`indexer.py:42-99`) to extract AI-generated summaries/entities per chunk is disruptive. It requires re-indexing all existing documents (expensive for 100k+ docs), changes the embedding dimensions or supplementary metadata schema, and the value depends on having features 1-3 in place to use the richer metadata.

**Prerequisite**: Stable AI service infrastructure from features 1-3.

---

## Implementation Plan

### Phase 1: Foundation + Query Enhancement

**New files**:
- `services/ai_service.py` — Anthropic API client wrapper with graceful degradation

**Modified files**:
- `config.py` — Add settings:
  ```python
  # AI Enhancement settings
  anthropic_api_key: Optional[str] = None
  ai_query_enhancement: bool = True       # Auto-enable if API key present
  ai_result_reranking: bool = False        # Opt-in
  ai_result_synthesis: bool = False        # Opt-in
  ai_model_query: str = "claude-haiku-4-20250514"
  ai_model_rerank: str = "claude-haiku-4-20250514"
  ai_model_synthesis: str = "claude-sonnet-4-20250514"
  ```
- `services/indexing/indexer.py` — Inject AI service, call `enhance_query()` before embedding
- `requirements.txt` — Add `anthropic>=0.40.0`

**Graceful degradation**: Every AI call is wrapped in try/except. If `anthropic_api_key` is None or empty, AI features are silently disabled. If an API call fails, the non-AI path executes.

### Phase 2: Result Reranking

**Modified files**:
- `services/ai_service.py` — Add `rerank_results()` method
- `services/indexing/indexer.py` — Call reranker after FAISS search, fetch extra results for reranking pool
- `models/schemas.py` — Add `rerank: Optional[bool] = False` to `SearchRequest`

### Phase 3: Result Synthesis

**Modified files**:
- `services/ai_service.py` — Add `synthesize_results()` method
- `models/schemas.py` — Add `synthesize: Optional[bool] = False` to `SearchRequest`, add `synthesis: Optional[str] = None` to `SearchResponse`
- `main.py` — Pass synthesis flag through search pipeline
- `frontend/src/components/SearchTab.vue` — Render synthesis above results list

### New API Endpoint (Optional)

Consider adding a dedicated endpoint for AI-enhanced search to keep the existing `/search` endpoint unchanged:

```
POST /search/ai
{
  "query": "...",
  "top_k": 10,
  "enhance_query": true,
  "rerank": true,
  "synthesize": true
}
```

This preserves backward compatibility while giving users explicit control over which AI features they want (and which costs they incur).

---

## Cost Transparency

A key design principle: users must understand what they're paying for.

**Proposed approach**: Include cost metadata in AI-enhanced responses:

```json
{
  "query": "database optimization",
  "results": [...],
  "synthesis": "Based on your documents...",
  "ai_usage": {
    "features_used": ["query_enhancement", "reranking", "synthesis"],
    "estimated_cost_usd": 0.012,
    "tokens_used": {
      "input": 3200,
      "output": 850
    },
    "models_used": ["claude-haiku-4-20250514", "claude-sonnet-4-20250514"]
  }
}
```

---

## Testing Strategy

### Without Burning API Credits

1. **Mock the Anthropic client**: Create a `MockAIService` that returns predetermined expansions, rankings, and syntheses for test queries.
2. **Record/replay**: Use `pytest-recording` or similar to capture real API responses once, then replay in CI.
3. **Integration test flag**: `ASYMPTOTE_TEST_AI=true` env var enables live API tests (run manually, not in CI).
4. **Quality benchmarks**: Create a small test corpus (10-20 documents) with known-good queries and expected results. Compare search quality with and without AI features.

### Test Matrix

| Feature | Test without API | Test with API |
|---|---|---|
| Query Enhancement | Mock returns original query | Verify expanded terms are relevant |
| Reranking | Mock returns original order | Verify precision@10 improves |
| Synthesis | Mock returns empty string | Verify citations match results |
| Degradation | Remove API key, verify all features still work | Simulate API errors |

---

## New Dependencies

| Package | Purpose | Size Impact |
|---|---|---|
| `anthropic>=0.40.0` | Anthropic API client | ~5MB (mostly httpx which is already installed) |

No other new dependencies required. The `httpx` package is already in `requirements.txt` for testing.

---

## Architectural Considerations

### API Key Management

**Option A (Recommended for v1)**: Server-side configuration via `.env`
```
ANTHROPIC_API_KEY=sk-ant-...
```
- Simpler to implement
- Single key for all users
- Fits the current single-tenant architecture

**Option B (Future)**: Per-request header
```
X-Anthropic-API-Key: sk-ant-...
```
- Enables multi-tenant usage
- Users control their own costs
- Requires frontend changes to collect and pass the key

Start with Option A; design the `AIService` to accept a key parameter so Option B is a future addition, not a rewrite.

### Async Considerations

The current search endpoint is `async` but calls synchronous code (`indexer.search()`). Anthropic's Python client supports both sync and async. For consistency with the existing pattern, use the sync client initially. If latency becomes an issue, switch to the async client and run embedding + AI calls concurrently where possible.

### Frontend Integration

The Vue 3 frontend (`frontend/src/components/SearchTab.vue`) currently renders a list of search results. For synthesis:

- Add a collapsible "AI Summary" card above the results list
- Show a loading spinner during the synthesis call (it will be slower than pure search)
- Display cost information in a subtle tooltip or footer
- Add a toggle in `SettingsTab.vue` for AI features (mirrors the server-side config)

---

## Summary Decision Matrix

| Feature | Value | Cost/Search | Complexity | Codebase Fit | Risk | Priority |
|---|---|---|---|---|---|---|
| Query Enhancement | High | $0.0001 | Low | Excellent | Low | **#1** |
| Result Reranking | High | $0.0005 | Medium | Excellent | Low-Med | **#2** |
| Result Synthesis | Very High | $0.015 | Med-High | Good | Medium | **#3** |
| Multi-Hop Search | Medium | $0.002 | High | Medium | High | Defer |
| Question Decomposition | Medium | $0.005 | High | Medium | High | Defer |
| Pre-Processing | High (long-term) | One-time | Very High | Low | High | Defer |

**Bottom line**: Query Enhancement and Result Reranking together cost under $0.001 per search and provide the best value-to-effort ratio. Result Synthesis is the feature that transforms the product but should be built on top of the first two.
