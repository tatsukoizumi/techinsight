"""Search endpoint: keyword / semantic / hybrid."""

from fastapi import APIRouter, Query

from app.core.deps import EmbedderDep, SessionDep
from app.schemas.article import ArticleRead, SearchResponse, SearchResultItem
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    session: SessionDep,
    embedder: EmbedderDep,
    q: str = Query(min_length=1),
    mode: search_service.SearchMode = "hybrid",
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
) -> SearchResponse:
    results = await search_service.search(
        session, embedder, query=q, mode=mode, limit=limit, category=category
    )
    items = [
        SearchResultItem(**ArticleRead.model_validate(article).model_dump(), score=score)
        for article, score in results
    ]
    return SearchResponse(items=items, total=len(items), mode=mode, query=q)
