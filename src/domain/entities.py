from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class ProductModel(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, unique=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, default="Masters of the Universe")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # Relationships
    offers: Mapped[List["OfferModel"]] = relationship(
        "OfferModel", 
        back_populates="product", 
        cascade="all, delete-orphan"
    )
    
    fortress_items: Mapped[List["FortressItemModel"]] = relationship(
        "FortressItemModel",
        back_populates="product",
        cascade="all, delete-orphan"
    )

class OfferModel(Base):
    __tablename__ = "offers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    
    shop_name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    url: Mapped[str] = mapped_column(String)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Analytics
    min_price: Mapped[float] = mapped_column(Float, default=0.0)
    max_price: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relationships
    product: Mapped["ProductModel"] = relationship("ProductModel", back_populates="offers")

class FortressItemModel(Base):
    __tablename__ = "collection_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    acquired: Mapped[bool] = mapped_column(Boolean, default=False)
    condition: Mapped[str] = mapped_column(String, default="New")
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Mapped["ProductModel"] = relationship("ProductModel", back_populates="fortress_items")
    owner: Mapped["UserModel"] = relationship("UserModel", back_populates="fortress_items")

# Update ProductModel to include relationship


class PendingMatchModel(Base):
    """
    Stores scraped items that weren't confidently matched to a Product.
    These sit in 'Purgatory' until the user assigns them.
    """
    __tablename__ = "pending_matches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Scraped Data
    scraped_name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    url: Mapped[str] = mapped_column(String, unique=True) # Avoid dupe pending items
    shop_name: Mapped[str] = mapped_column(String)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Optional logic: Store "Best Guess" match?
    # suggested_product_id: Mapped[Optional[int]]


class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="viewer") # admin, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ScraperStatusModel(Base):
    __tablename__ = "scraper_status"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spider_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String) # running, completed, error
    items_scraped: Mapped[int] = mapped_column(Integer, default=0)
    total_items_estimated: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BlackcludedItemModel(Base):
    """Items explicitly discarded by the user to prevent re-scraping."""
    __tablename__ = "blackcluded_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    scraped_name: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String, default="user_discarded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Force Reload Trigger: v2.1
