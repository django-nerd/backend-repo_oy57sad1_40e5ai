from typing import List, Optional
from pydantic import BaseModel, Field

# Imperial Essence Schemas

class Product(BaseModel):
    name: str
    brand: str
    price: float = Field(ge=0)
    image: Optional[str] = None
    notes: Optional[List[str]] = None

class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)

class Order(BaseModel):
    items: List[CartItem]
    subtotal: float = Field(ge=0)
    discount_code: Optional[str] = None
    discount_amount: float = Field(ge=0, default=0)
    total: float = Field(ge=0)
