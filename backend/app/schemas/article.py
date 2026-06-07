"""Pydantic v2 schemas for the articles API (request/response I/O only)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArticleBase(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    author: str = Field(min_length=1)
    category: str = Field(min_length=1)
    published_at: datetime


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1)
    published_at: datetime | None = None


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ArticleList(BaseModel):
    items: list[ArticleRead]
    total: int
    page: int
    size: int


class SearchResultItem(ArticleRead):
    score: float


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    mode: str
    query: str
