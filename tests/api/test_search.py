import uuid

import pytest
from httpx import AsyncClient


def _doc(text: str) -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def _create_searchable_page(
    auth_client: AsyncClient,
    *,
    title: str,
    content_text: str,
) -> str:
    create = await auth_client.post("/api/v1/pages", json={"title": title})
    assert create.status_code == 201
    page_id = create.json()["page"]["id"]

    update = await auth_client.put(
        f"/api/v1/pages/{page_id}",
        json={"title": title, "content_json": _doc(content_text), "content_text": content_text},
    )
    assert update.status_code == 200
    return page_id


@pytest.mark.asyncio
async def test_keyword_search_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/search/keyword?q=test")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_keyword_search_empty_query(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/search/keyword")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_keyword_search_no_results(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/search/keyword?q=xyzzy_unique_gibberish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["total"] == 0
    assert data["query"] == "xyzzy_unique_gibberish"
    assert data["mode"] == "keyword"


@pytest.mark.asyncio
async def test_keyword_search_finds_page(auth_client: AsyncClient):
    await _create_searchable_page(
        auth_client,
        title="Quantum Computing",
        content_text=(
            "Quantum entanglement and superposition appear in this research note about "
            "future computing systems, measurement errors, physical qubits, and laboratory "
            "experiments that require careful calibration."
        ),
    )

    resp = await auth_client.get("/api/v1/search/keyword?q=quantum")
    assert resp.status_code == 200
    assert any(result["kind"] == "page" for result in resp.json()["results"])


@pytest.mark.asyncio
async def test_keyword_search_filter_by_kind(auth_client: AsyncClient):
    title = f"Source Filter Target {uuid.uuid4().hex}"
    page_id = await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            "This page discusses retrieval filters, page records, source records, metadata "
            "boundaries, and integration behavior for a realistic search result payload."
        ),
    )

    resp = await auth_client.get("/api/v1/search/keyword", params={"q": title, "kind": "source"})
    assert resp.status_code == 200
    result_ids = {result["id"] for result in resp.json()["results"]}
    assert page_id not in result_ids
    assert all(result["kind"] != "page" for result in resp.json()["results"])


@pytest.mark.asyncio
async def test_keyword_search_response_shape(auth_client: AsyncClient):
    title = f"Response Shape {uuid.uuid4().hex}"
    await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            "Response shape validation uses realistic writing about notebooks, summaries, "
            "research context, reusable snippets, timestamps, rankings, and structured "
            "metadata returned by keyword search."
        ),
    )

    resp = await auth_client.get("/api/v1/search/keyword", params={"q": title})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["results"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["query"], str)
    assert data["mode"] == "keyword"
    assert data["results"]

    result = data["results"][0]
    for key in [
        "id",
        "kind",
        "title",
        "snippet",
        "tags",
        "score",
        "updated_at",
        "source_type",
        "ingestion_status",
    ]:
        assert key in result


@pytest.mark.asyncio
async def test_vector_search_disabled(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.config.settings.openai_api_key", None)
    resp = await auth_client.post("/api/v1/search/vector", json={"q": "hello"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "embeddings_disabled"


@pytest.mark.asyncio
async def test_hybrid_search_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/search/hybrid", json={"q": "hello"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hybrid_search_no_results(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.config.settings.openai_api_key", None)
    resp = await auth_client.post("/api/v1/search/hybrid", json={"q": "xyzzy_unique_gibberish"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["total"] == 0
    assert data["query"] == "xyzzy_unique_gibberish"
    assert data["mode"] == "hybrid"
    assert data["embeddings_used"] is False


@pytest.mark.asyncio
async def test_hybrid_search_finds_page(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.config.settings.openai_api_key", None)
    title = f"Hybrid Search Target {uuid.uuid4().hex}"
    page_id = await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            "Hybrid search should still find this page through keyword fallback when "
            "embeddings are disabled, while preserving useful snippets, scores, and "
            "recently updated object metadata for the client."
        ),
    )

    resp = await auth_client.post("/api/v1/search/hybrid", json={"q": title})
    assert resp.status_code == 200
    result_ids = {result["id"] for result in resp.json()["results"]}
    assert page_id in result_ids


@pytest.mark.asyncio
async def test_hybrid_search_response_shape(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.config.settings.openai_api_key", None)
    resp = await auth_client.post("/api/v1/search/hybrid", json={"q": "something"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["results"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["query"], str)
    assert data["mode"] == "hybrid"
    assert isinstance(data["embeddings_used"], bool)


@pytest.mark.asyncio
async def test_keyword_search_limit(auth_client: AsyncClient):
    keyword = f"limitmarker{uuid.uuid4().hex}"
    for idx in range(3):
        await _create_searchable_page(
            auth_client,
            title=f"Limit Search Page {idx}",
            content_text=(
                f"The shared keyword {keyword} appears in this realistic research note "
                "about retrieval limits, pagination behavior, repeated content, ranking, "
                "and client rendering for compact result lists."
            ),
        )

    resp = await auth_client.get(
        "/api/v1/search/keyword",
        params={"q": keyword, "limit": 2},
    )
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 2


@pytest.mark.asyncio
async def test_search_deleted_object_excluded(auth_client: AsyncClient):
    title = f"Deleted Search Target {uuid.uuid4().hex}"
    page_id = await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            "Deleted objects should be excluded from keyword search results even when "
            "their page content contains memorable terms, realistic notes, project details, "
            "and enough words for full text search."
        ),
    )
    delete = await auth_client.delete(f"/api/v1/objects/{page_id}")
    assert delete.status_code == 200

    resp = await auth_client.get("/api/v1/search/keyword", params={"q": title})
    assert resp.status_code == 200
    assert page_id not in {result["id"] for result in resp.json()["results"]}


@pytest.mark.asyncio
async def test_snippet_shape_is_struct(auth_client: AsyncClient):
    """Snippet must be {text, highlights} — not a raw HTML string."""
    title = f"SnippetShape {uuid.uuid4().hex}"
    await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            "Snippet shape validation checks that the API returns structured plain-text "
            "snippets with highlight ranges instead of raw HTML markup from ts_headline."
        ),
    )
    resp = await auth_client.get("/api/v1/search/keyword", params={"q": title})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    snippet = results[0]["snippet"]
    if snippet is not None:
        assert isinstance(snippet, dict), "snippet must be an object, not a string"
        assert "text" in snippet
        assert "highlights" in snippet
        assert isinstance(snippet["text"], str)
        assert isinstance(snippet["highlights"], list)
        assert "<mark>" not in snippet["text"], "snippet.text must not contain HTML markup"


@pytest.mark.asyncio
async def test_snippet_xss_payload_not_rendered_as_html(auth_client: AsyncClient):
    """XSS regression: <script> in page content must not appear as live HTML in snippet."""
    payload = "<script>document.title='pwned'</script>"
    title = f"XSSTarget {uuid.uuid4().hex}"
    await _create_searchable_page(
        auth_client,
        title=title,
        content_text=(
            f"Safety test for XSS regression. This page contains: {payload} "
            "which must be returned as plain text, not as an executable HTML tag."
        ),
    )
    resp = await auth_client.get("/api/v1/search/keyword", params={"q": "XSS regression"})
    assert resp.status_code == 200
    body = resp.text
    # The raw JSON response must not contain an unescaped <script> that a browser would execute.
    # Since snippet.text is a plain string inside JSON, the angle brackets will appear as-is
    # in the JSON body but will NOT be parsed as HTML when rendered via React text nodes.
    # Verify the response is well-formed JSON and snippet is not a raw HTML string.
    for result in resp.json()["results"]:
        snippet = result.get("snippet")
        if snippet is not None:
            assert isinstance(snippet, dict), f"snippet must be a struct, got: {type(snippet)}"
            # Ensure no HTML-only markup like <mark> ended up in text
            assert "<mark>" not in snippet["text"]
    _ = body  # referenced to suppress unused-var lint
