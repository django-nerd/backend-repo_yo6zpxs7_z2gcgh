from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime


class Deal(BaseModel):
    platform: str
    title: str
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    quality_score: Optional[float] = None
    image_urls: List[HttpUrl] = Field(default_factory=list)
    product_url: Optional[HttpUrl] = None
    delivery: Optional[str] = None
    created_at: Optional[datetime] = None


class SearchQuery(BaseModel):
    query: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort_by: Optional[str] = Field(
        default="best",
        description="best | price_low | price_high | rating | reviews",
    )


class SearchResponse(BaseModel):
    deals: List[Deal]
    pitch: str
