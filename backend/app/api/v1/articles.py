"""CRUD endpoints for articles."""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import EmbedderDep, SessionDep
from app.repositories import article as repo
from app.schemas.article import ArticleCreate, ArticleList, ArticleRead, ArticleUpdate
from app.services import articles as service

router = APIRouter(prefix="/articles", tags=["articles"])


async def _get_or_404(session: SessionDep, article_id: int):
    article = await repo.get(session, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@router.get("", response_model=ArticleList)
async def list_articles(
    session: SessionDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    author: str | None = None,
    sort: repo.Sort = "newest",
) -> ArticleList:
    items, total = await repo.list_articles(
        session, page=page, size=size, category=category, author=author, sort=sort
    )
    return ArticleList(items=items, total=total, page=page, size=size)


@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, session: SessionDep) -> ArticleRead:
    return await _get_or_404(session, article_id)


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate, session: SessionDep, embedder: EmbedderDep
) -> ArticleRead:
    return await service.create_article(session, embedder, data)


@router.put("/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: int, data: ArticleUpdate, session: SessionDep, embedder: EmbedderDep
) -> ArticleRead:
    article = await _get_or_404(session, article_id)
    return await service.update_article(session, embedder, article, data)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: int, session: SessionDep) -> None:
    article = await _get_or_404(session, article_id)
    await repo.delete(session, article)
