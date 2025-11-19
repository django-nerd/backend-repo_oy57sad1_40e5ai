from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

# Each class => one collection, lowercased name

class Product(BaseModel):
    name: str
    brand: str
    category: str = "fragrance"
    description: Optional[str] = None
    price: float
    stock: int = 0
    image: Optional[str] = None
    notes: Optional[list[str]] = None

class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, default=1)

class Order(BaseModel):
    items: list[CartItem]
    subtotal: float
    discount_code: Optional[str] = None
    discount_amount: float = 0
    total: float
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
