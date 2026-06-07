"""Aggregated /api/v1 router."""

from fastapi import APIRouter

from app.api.v1 import articles, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(articles.router)
api_router.include_router(search.router)
