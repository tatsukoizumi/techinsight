"""Integration tests for the articles CRUD API."""

from __future__ import annotations

from httpx import AsyncClient

SAMPLE = {
    "title": "Implementing PostgreSQL indexes",
    "content": "A guide to GIN and HNSW indexes in postgres.",
    "author": "Ito",
    "category": "Backend",
    "published_at": "2025-01-02T03:04:05Z",
}


async def test_create_get_update_delete(client: AsyncClient) -> None:
    # create
    resp = await client.post("/api/v1/articles", json=SAMPLE)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    article_id = created["id"]
    assert created["title"] == SAMPLE["title"]
    assert "embedding" not in created  # never leak internal columns

    # get
    resp = await client.get(f"/api/v1/articles/{article_id}")
    assert resp.status_code == 200
    assert resp.json()["author"] == "Ito"

    # update (partial)
    resp = await client.put(f"/api/v1/articles/{article_id}", json={"author": "Tanaka"})
    assert resp.status_code == 200
    assert resp.json()["author"] == "Tanaka"
    assert resp.json()["title"] == SAMPLE["title"]

    # delete
    resp = await client.delete(f"/api/v1/articles/{article_id}")
    assert resp.status_code == 204

    # gone
    resp = await client.get(f"/api/v1/articles/{article_id}")
    assert resp.status_code == 404


async def test_get_missing_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/articles/999999")
    assert resp.status_code == 404


async def test_create_validation_error(client: AsyncClient) -> None:
    bad = {**SAMPLE, "title": ""}
    resp = await client.post("/api/v1/articles", json=bad)
    assert resp.status_code == 422


async def test_list_pagination_and_filter(client: AsyncClient) -> None:
    for i in range(3):
        await client.post(
            "/api/v1/articles",
            json={**SAMPLE, "title": f"Doc {i}", "category": "Backend" if i < 2 else "DevOps"},
        )

    resp = await client.get("/api/v1/articles", params={"page": 1, "size": 2})
    body = resp.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["size"] == 2
    assert len(body["items"]) == 2

    resp = await client.get("/api/v1/articles", params={"category": "DevOps"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "DevOps"
