"""Search tests: keyword and semantic retrieval over a real pgvector PG."""

from __future__ import annotations

from httpx import AsyncClient


async def _create(client: AsyncClient, title: str, content: str, category: str = "Backend") -> int:
    resp = await client.post(
        "/api/v1/articles",
        json={
            "title": title,
            "content": content,
            "author": "Author",
            "category": category,
            "published_at": "2025-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_keyword_search(client: AsyncClient) -> None:
    await _create(client, "PostgreSQL indexing", "gin and hnsw indexes")
    react_id = await _create(client, "React hooks", "useState and effects")

    resp = await client.get("/api/v1/search", params={"q": "react", "mode": "keyword"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "keyword"
    assert [item["id"] for item in body["items"]] == [react_id]
    assert "score" in body["items"][0]


async def test_semantic_ranking(client: AsyncClient) -> None:
    # FakeEmbedder maps these to distinct keyword axes.
    pg_id = await _create(client, "Backend storage", "tuning postgres for scale")
    await _create(client, "Frontend", "building react components")

    resp = await client.get(
        "/api/v1/search", params={"q": "postgres performance", "mode": "semantic"}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["id"] == pg_id  # closest by cosine similarity
    assert items[0]["score"] > items[-1]["score"]


async def test_semantic_category_filter(client: AsyncClient) -> None:
    await _create(client, "Backend postgres", "postgres tuning", category="Backend")
    devops_id = await _create(client, "DevOps postgres", "postgres on k8s", category="DevOps")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "postgres", "mode": "semantic", "category": "DevOps"},
    )
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids == [devops_id]
