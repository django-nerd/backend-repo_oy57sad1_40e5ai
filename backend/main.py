from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from database import create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="Imperial Essence API")

# Allow all origins for dev preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed data: popular Oud and luxury perfumes
SEED_PRODUCTS: list[dict] = [
    {"name": "Acqua di Parma Colonia Oud", "brand": "Acqua di Parma", "price": 280.0, "stock": 25, "image": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?q=80&w=1600&auto=format&fit=crop", "notes": ["Oud", "Citrus", "Leather"]},
    {"name": "Maison Francis Kurkdjian Oud Satin Mood", "brand": "MFK", "price": 325.0, "stock": 30, "image": "https://images.unsplash.com/photo-1616617435710-3a2e49963cf1?q=80&w=1600&auto=format&fit=crop", "notes": ["Oud", "Vanilla", "Rose"]},
    {"name": "Tom Ford Oud Wood", "brand": "Tom Ford", "price": 290.0, "stock": 40, "image": "https://images.unsplash.com/photo-1563170351-be82bc888aa4?q=80&w=1600&auto=format&fit=crop", "notes": ["Oud", "Cardamom", "Sandalwood"]},
    {"name": "Dior Sauvage Elixir", "brand": "Dior", "price": 195.0, "stock": 60, "image": "https://images.unsplash.com/photo-1613487227375-6f3d7447d3cc?q=80&w=1600&auto=format&fit=crop", "notes": ["Spicy", "Lavender", "Woods"]},
    {"name": "Creed Aventus", "brand": "Creed", "price": 365.0, "stock": 35, "image": "https://images.unsplash.com/photo-1618568949770-70fddd9f4bcd?q=80&w=1600&auto=format&fit=crop", "notes": ["Pineapple", "Birch", "Musk"]},
    {"name": "Roja Parfums Enigma", "brand": "Roja Parfums", "price": 485.0, "stock": 15, "image": "https://images.unsplash.com/photo-1585386959984-a41552231655?q=80&w=1600&auto=format&fit=crop", "notes": ["Tobacco", "Vanilla", "Amber"]},
    {"name": "Amouage Interlude Man", "brand": "Amouage", "price": 340.0, "stock": 20, "image": "https://images.unsplash.com/photo-1592462548162-5d2b33da5c7e?q=80&w=1600&auto=format&fit=crop", "notes": ["Oregano", "Amber", "Oud"]},
    {"name": "Initio Oud for Greatness", "brand": "Initio", "price": 360.0, "stock": 18, "image": "https://images.unsplash.com/photo-1509840841025-9088ba78a826?q=80&w=1600&auto=format&fit=crop", "notes": ["Oud", "Saffron", "Patchouli"]},
    {"name": "Le Labo Santal 33", "brand": "Le Labo", "price": 310.0, "stock": 50, "image": "https://images.unsplash.com/photo-1611931932169-0d41e2a2d283?q=80&w=1600&auto=format&fit=crop", "notes": ["Sandalwood", "Cedar", "Leather"]},
    {"name": "Byredo Black Saffron", "brand": "Byredo", "price": 290.0, "stock": 25, "image": "https://images.unsplash.com/photo-1605971816925-0f6bdd3e5d43?q=80&w=1600&auto=format&fit=crop", "notes": ["Saffron", "Berry", "Leather"]},
]

class SeedResponse(BaseModel):
    inserted: int

@app.post("/seed", response_model=SeedResponse)
async def seed_products():
    # Insert only if products collection is empty
    from database import get_db
    db = await get_db()
    count = await db["product"].count_documents({})
    if count == 0:
        for p in SEED_PRODUCTS:
            await create_document("product", Product(**p).model_dump())
        return SeedResponse(inserted=len(SEED_PRODUCTS))
    return SeedResponse(inserted=0)

class ProductOut(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    description: Optional[str] = None
    price: float
    stock: int
    image: Optional[str] = None
    notes: Optional[list[str]] = None

@app.get("/products", response_model=list[ProductOut])
async def list_products(q: Optional[str] = Query(None), brand: Optional[str] = Query(None)):
    filter_dict = {}
    if q:
        # Simple case-insensitive name search
        filter_dict["name"] = {"$regex": q, "$options": "i"}
    if brand:
        filter_dict["brand"] = {"$regex": brand, "$options": "i"}

    docs = await get_documents("product", filter_dict, limit=200)
    return [ProductOut(**d) for d in docs]

# Discount codes
DISCOUNTS = {
    "IMPERIAL10": 0.10,
    "OUD15": 0.15,
    "ROYAL20": 0.20,
}

class DiscountCheck(BaseModel):
    code: str

class DiscountOut(BaseModel):
    valid: bool
    percent: float = 0

@app.post("/discount", response_model=DiscountOut)
async def check_discount(payload: DiscountCheck):
    code = payload.code.strip().upper()
    if code in DISCOUNTS:
        return DiscountOut(valid=True, percent=DISCOUNTS[code])
    return DiscountOut(valid=False, percent=0)

class OrderOut(BaseModel):
    id: str

@app.post("/order", response_model=OrderOut)
async def create_order(order: Order):
    # Compute totals server-side for safety
    percent = DISCOUNTS.get((order.discount_code or "").upper(), 0)
    discount_amount = round(order.subtotal * percent, 2)
    total = round(order.subtotal - discount_amount, 2)
    saved = await create_document("order", {
        **order.model_dump(),
        "discount_amount": discount_amount,
        "total": total,
    })
    return OrderOut(id=saved.get("id", ""))

@app.get("/test")
async def test():
    return {"ok": True}
