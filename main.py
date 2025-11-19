import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from database import db, create_document, get_documents
from schemas import Product as ProductSchema, CartItem, Order as OrderSchema

app = FastAPI(title="Imperial Essence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCOUNT_CODES = {
    "IMPERIAL10": 0.10,
    "OUD15": 0.15,
    "ROYAL20": 0.20,
}

# Utils

def product_to_client(doc):
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "brand": doc.get("brand"),
        "price": float(doc.get("price", 0)),
        "image": doc.get("image"),
        "notes": doc.get("notes", []),
    }

@app.get("/")
async def root():
    return {"message": "Imperial Essence Backend Running"}

@app.get("/test")
async def test():
    try:
        ok = db is not None
        colls = []
        db_name = None
        if ok:
            db_name = db.name
            try:
                colls = db.list_collection_names()
            except Exception:
                pass
        return {
            "backend": "✅ Running",
            "database": "✅ Available" if ok else "❌ Not Available",
            "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
            "database_name": db_name or ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"),
            "connection_status": "Connected" if ok else "Not Connected",
            "collections": colls,
        }
    except Exception as e:
        return {"backend": "Error", "error": str(e)}

@app.post("/seed")
async def seed():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    products_col = db["product"]
    if products_col.count_documents({}) > 0:
        return {"seeded": False, "message": "Products already exist"}
    seed_products: List[dict] = [
        {
            "name": "Oud Royale",
            "brand": "Imperial House",
            "price": 320.0,
            "image": "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=1200&auto=format&fit=crop",
            "notes": ["Oud", "Rose", "Saffron"],
        },
        {
            "name": "Santal Majesté",
            "brand": "Maison Étoile",
            "price": 280.0,
            "image": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?q=80&w=1200&auto=format&fit=crop",
            "notes": ["Sandalwood", "Vanilla", "Cardamom"],
        },
        {
            "name": "Amber Imperial",
            "brand": "Crown Atelier",
            "price": 250.0,
            "image": "https://images.unsplash.com/photo-1605979344330-79b0fd9005d3?q=80&w=1200&auto=format&fit=crop",
            "notes": ["Amber", "Cedar", "Musk"],
        },
        {
            "name": "Rose des Sultans",
            "brand": "Maison Étoile",
            "price": 300.0,
            "image": "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?q=80&w=1200&auto=format&fit=crop",
            "notes": ["Rose", "Oud", "Patchouli"],
        },
    ]
    for p in seed_products:
        create_document("product", p)
    return {"seeded": True, "count": len(seed_products)}

@app.get("/products")
async def get_products(q: Optional[str] = Query(None), brand: Optional[str] = Query(None)):
    if db is None:
        return []
    filt = {}
    if q:
        filt["name"] = {"$regex": q, "$options": "i"}
    if brand:
        filt["brand"] = brand
    docs = get_documents("product", filt)
    return [product_to_client(d) for d in docs]

class DiscountIn(BaseModel):
    code: str

@app.post("/discount")
async def discount_check(payload: DiscountIn):
    code = payload.code.strip().upper()
    percent = DISCOUNT_CODES.get(code, 0)
    return {"valid": percent > 0, "percent": percent}

@app.post("/order")
async def create_order(order: OrderSchema):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Fetch item prices from DB to prevent tampering
    prod_col = db["product"]
    subtotal = 0.0
    items_to_store = []
    for item in order.items:
        try:
            doc = prod_col.find_one({"_id": ObjectId(item.product_id)})
        except Exception:
            doc = None
        if not doc:
            raise HTTPException(status_code=400, detail=f"Invalid product {item.product_id}")
        price = float(doc.get("price", 0))
        subtotal += price * item.quantity
        items_to_store.append({
            "product_id": item.product_id,
            "name": doc.get("name"),
            "price": price,
            "quantity": item.quantity,
        })

    code = (order.discount_code or "").strip().upper()
    percent = DISCOUNT_CODES.get(code, 0)
    discount_amount = round(subtotal * percent, 2)
    total = round(max(0.0, subtotal - discount_amount), 2)

    order_doc = {
        "items": items_to_store,
        "subtotal": round(subtotal, 2),
        "discount_code": code if percent > 0 else None,
        "discount_amount": discount_amount,
        "total": total,
    }
    order_id = create_document("order", order_doc)
    return {"id": order_id, **order_doc}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
