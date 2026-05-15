# Search Evaluation Guide

## Why Eval Cases Exist

Search quality is hard to verify with pure unit tests. A keyword search might return rows without actually surfacing the right content; a hybrid search might merge results in a way that buries the most relevant object. Eval cases capture the user-facing contract: given this query, these kinds of objects should appear.

The fixtures in `tests/fixtures/search_eval_cases.json` act as regression anchors. Each case has a human-readable `notes` field explaining what should happen and why. When a search change causes a previously passing eval case to fail, that is a signal — not necessarily a bug, but something to review before merging.

## File Format

```json
{
  "id": "unique-slug",
  "query": "user query text",
  "expected_kinds": ["page", "source"],
  "filter_kind": "page",
  "modes": ["keyword", "hybrid", "vector"],
  "notes": "Human-readable explanation of what should happen and why."
}
```

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | Unique slug; used as test ID in pytest output |
| `query` | Yes | The search query string |
| `expected_kinds` | Yes | `kind` values that should appear in results; `[]` means expect empty results |
| `filter_kind` | No | If set, the API call should include `?kind=<value>` |
| `modes` | Yes | Which search modes this case applies to: `keyword`, `vector`, `hybrid` |
| `notes` | Yes | Explain the intent; written for the next engineer, not for the machine |

## How Tests Use Eval Cases

Phase 3 introduces `tests/api/test_search.py`. It loads the fixture file and runs cases against the live test database:

```python
import json, pytest
CASES = json.loads(open("fixtures/search_eval_cases.json").read())

@pytest.mark.parametrize("case", [c for c in CASES if "keyword" in c["modes"]])
async def test_keyword_eval_cases(case, client, seeded_db):
    resp = await client.get(f"/api/v1/search/keyword?q={case['query']}")
    kinds = {r["kind"] for r in resp.json()["items"]}
    if case["expected_kinds"]:
        assert any(k in kinds for k in case["expected_kinds"]), (
            f"Case {case['id']}: expected one of {case['expected_kinds']} but got {kinds}"
        )
    else:
        assert len(resp.json()["items"]) == 0
```

The `seeded_db` fixture creates representative pages and sources before each test run.

## Adding New Cases

1. Open `tests/fixtures/search_eval_cases.json`.
2. Add a new case object with a unique `id`.
3. Write a clear `notes` field — future engineers will read this to understand intent.
4. Set `modes` correctly: `keyword` works without an API key; `vector` requires one.
5. Run `cd tests && uv run pytest api/test_search.py -k eval -v` to verify the new case passes.

**When to add a case:**
- When you discover a real-user query that the system should handle but doesn't yet
- After fixing a search regression — add the query that caught the bug
- When adding a new object kind — add at least one case verifying it's searchable

## Connection to Phase 5 AI Q&A

These same eval cases are the ground-truth inputs for Phase 5 RAG evaluation. When the AI assistant answers from the knowledge base, the eval cases verify that the retrieval stage finds the right context before the LLM generates an answer. Adding high-quality eval cases pays dividends in all AI-backed search and Q&A flows.

## Offline/Keyword-Only Behavior

Cases with `"modes": ["keyword"]` must pass with no `OPENAI_API_KEY` set. Cases with `"modes": ["vector"]` are expected to return graceful errors or be skipped when the embedding provider is unavailable. Hybrid cases should fall back to keyword-only results when embeddings are disabled.
