from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import math
import os
from datetime import datetime

from schemas import Deal, SearchQuery, SearchResponse

app = FastAPI(title="E-commerce Deals Chatbot API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper scoring and formatting
PLATFORMS = ["amazon", "flipkart", "myntra", "ajio"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _norm(v: Optional[float], lo: float, hi: float) -> float:
    if v is None:
        return 0.0
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def score_deal(price: Optional[float], rating: Optional[float], reviews: Optional[int]) -> float:
    # Lower price is better, higher rating and reviews better
    price_score = 0.0
    if price is not None:
        # heuristic: normalize vs. assumed range
        price_score = 1.0 - _norm(price, 100.0, 50000.0)
    rating_score = 0.0 if rating is None else (rating / 5.0)
    reviews_score = 0.0
    if reviews is not None:
        reviews_score = min(1.0, math.log10(max(1, reviews)) / 3)
    # Weighted blend
    return round(0.5 * price_score + 0.35 * rating_score + 0.15 * reviews_score, 4)


async def scrape_stub(query: str) -> List[Deal]:
    # NOTE: Real e-commerce sites have anti-bot protection and ToS restrictions for scraping.
    # Here we provide a safe demo using public placeholder data. In production, integrate
    # approved affiliate/search APIs or your own indexed catalog.
    demo_images = [
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9",
        "https://images.unsplash.com/photo-1512499617640-c2f999098c01",
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
        "https://images.unsplash.com/photo-1526178610626-3f118bb11566",
    ]
    base_price = 999.0
    platforms = [
        ("amazon", 0.0, 4.5, 1250),
        ("flipkart", -50.0, 4.3, 980),
        ("myntra", 120.0, 4.6, 540),
        ("ajio", -100.0, 4.2, 330),
    ]
    deals: List[Deal] = []
    for i, (pf, delta, rating, reviews) in enumerate(platforms):
        price = max(99.0, base_price + delta)
        original = price * 1.25
        discount = round((1 - price / original) * 100, 2)
        deals.append(
            Deal(
                platform=pf,
                title=f"{query.title()} – Top Pick #{i+1}",
                price=round(price, 2),
                original_price=round(original, 2),
                discount_percent=discount,
                rating=rating,
                reviews_count=reviews,
                quality_score=score_deal(price, rating, reviews),
                image_urls=demo_images,
                product_url=f"https://{pf}.com/s?k=" + query.replace(" ", "+"),
                delivery="Fast delivery in 2-4 days",
                created_at=datetime.utcnow(),
            )
        )
    # Sort by composite quality score descending
    deals.sort(key=lambda d: d.quality_score or 0, reverse=True)
    return deals


def craft_pitch(query: str, deals: List[Deal]) -> str:
    if not deals:
        return (
            f"I couldn't find great matches for ‘{query}’ right now. "
            "Try refining the product name or category, and I'll hunt for fresh deals."
        )
    best = deals[0]
    alt = ", ".join([f"{d.platform.capitalize()} at ₹{int(d.price)}" for d in deals[1:3]])
    return (
        f"If you're looking for {query}, my best pick is on {best.platform.capitalize()} at ₹{int(best.price)} "
        f"with {best.discount_percent}% off and a solid {best.rating}★ from {best.reviews_count}+ reviews. "
        f"I can also get you options from {alt}. Want me to open the best offer for you?"
    )


@app.get("/")
async def root():
    return {"status": "ok", "service": "deals-bot"}


@app.post("/search", response_model=SearchResponse)
async def search_deals(payload: SearchQuery):
    # In production: call official APIs, affiliate networks, or your own indexing.
    deals = await scrape_stub(payload.query)

    # Apply client-side price filters
    if payload.min_price is not None:
        deals = [d for d in deals if d.price >= payload.min_price]
    if payload.max_price is not None:
        deals = [d for d in deals if d.price <= payload.max_price]

    # Sort
    if payload.sort_by == "price_low":
        deals.sort(key=lambda d: d.price)
    elif payload.sort_by == "price_high":
        deals.sort(key=lambda d: d.price, reverse=True)
    elif payload.sort_by == "rating":
        deals.sort(key=lambda d: (d.rating or 0), reverse=True)
    elif payload.sort_by == "reviews":
        deals.sort(key=lambda d: (d.reviews_count or 0), reverse=True)
    else:  # best
        deals.sort(key=lambda d: (d.quality_score or 0), reverse=True)

    pitch = craft_pitch(payload.query, deals)
    return SearchResponse(deals=deals, pitch=pitch)


@app.get("/test")
async def test():
    # Simple health check endpoint
    return {"ok": True}
