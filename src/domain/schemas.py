from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, List

# --- Shared Properties ---
class OfferBase(BaseModel):
    shop_name: str
    price: float = Field(gt=0, description="Price in EUR")
    url: str # Keeping as str to avoid validation issues with some scraped URLs, validated in logic
    currency: str = "EUR"
    is_available: bool = True

class ProductBase(BaseModel):
    name: str = Field(min_length=1)
    ean: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = "Masters of the Universe"

# --- Creation Schemas ---
class OfferCreate(OfferBase):
    product_id: int

class ProductCreate(ProductBase):
    pass

# --- Reading Schemas (Return from DB) ---
class Offer(OfferBase):
    id: int
    last_seen: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    offers: List[Offer] = []
    is_owned: bool = False # Computable field

    model_config = ConfigDict(from_attributes=True)

class CollectionItemCreate(BaseModel):
    product_id: int
    acquired: bool = True
    notes: Optional[str] = None

class CollectionItem(CollectionItemCreate):
    id: int
    acquired_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
