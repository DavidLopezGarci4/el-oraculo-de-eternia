from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import List, Optional

DOMAIN_VERSION = "1.2.1-GUARDIAN"

from src.domain.base import Base

# PriceAlertModel moved down for dependency resolution

class ProductModel(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, unique=True)
    ean: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, default="Masters of the Universe")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    offers: Mapped[List["OfferModel"]] = relationship(
        "OfferModel", 
        back_populates="product", 
        cascade="all, delete-orphan"
    )
    
    collection_items: Mapped[List["CollectionItemModel"]] = relationship(
        "CollectionItemModel",
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
    price_history: Mapped[List["PriceHistoryModel"]] = relationship(
        "PriceHistoryModel", 
        back_populates="offer",
        cascade="all, delete-orphan"
    )

class CollectionItemModel(Base):
    __tablename__ = "collection_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=False) # Allow multiple users to own same product
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id")) # Link to User
    
    acquired: Mapped[bool] = mapped_column(Boolean, default=False)
    condition: Mapped[str] = mapped_column(String, default="New")
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Mapped["ProductModel"] = relationship("ProductModel", back_populates="collection_items")
    owner: Mapped["UserModel"] = relationship("UserModel", back_populates="collection_items")

# Update ProductModel to include relationship
ProductModel.collection_item = relationship(
    "CollectionItemModel", 
    uselist=False, 
    back_populates="product",
    cascade="all, delete-orphan",
    overlaps="collection_items"
)

class PendingMatchModel(Base):
    """
    Stores scraped items that weren't confidently matched to a Product.
    These sit in 'Purgatory' until the user assigns them.
    """
    __tablename__ = "pending_matches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Scraped Data
    scraped_name: Mapped[str] = mapped_column(String)
    ean: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    url: Mapped[str] = mapped_column(String, unique=True) # Avoid dupe pending items
    shop_name: Mapped[str] = mapped_column(String)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
# PriceAlertModel promoted to top (moved here for coherence)
class PriceAlertModel(Base):
    """
    Vigilancia de precios del Centinela.
    """
    __tablename__ = "price_alerts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    target_price: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    product: Mapped["ProductModel"] = relationship("ProductModel")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="price_alerts")



class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=False) # Changed to False to allow admin/user same email
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="viewer") # admin, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    price_alerts: Mapped[List["PriceAlertModel"]] = relationship("PriceAlertModel", back_populates="user", cascade="all, delete-orphan")
    collection_items: Mapped[List["CollectionItemModel"]] = relationship(
        "CollectionItemModel",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

class ScraperStatusModel(Base):
    __tablename__ = "scraper_status"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spider_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String) # running, completed, error
    items_scraped: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0) # 0-100
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

class PriceHistoryModel(Base):
    """Tracks price changes over time for analytics."""
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"))
    price: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    offer: Mapped["OfferModel"] = relationship("OfferModel", back_populates="price_history")

class ScraperExecutionLogModel(Base):
    """
    Immutable log of every scraper execution run.
    Provides forensic history and audit trail.
    """
    __tablename__ = "scraper_execution_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spider_name: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String) # success, error, interrupted
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    new_items: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Context
    trigger_type: Mapped[str] = mapped_column(String, default="manual") # manual, scheduled
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class KaizenInsightModel(Base):
    """
    Qualitative repository for anti-bot findings, DOM changes, and improvement ideas.
    This is the primary source of 'Trial & Error' knowledge.
    """
    __tablename__ = "kaizen_insights"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spider_name: Mapped[str] = mapped_column(String, index=True)
    
    insight_type: Mapped[str] = mapped_column(String) # dom_change, anti_bot_detected, idea, improvement
    severity: Mapped[str] = mapped_column(String, default="info") # info, warning, critical
    
    content: Mapped[str] = mapped_column(String) # Detailed description
    pattern_observed: Mapped[Optional[str]] = mapped_column(String, nullable=True) # CSS selectors, timing, etc.
    proposed_solution: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    status: Mapped[str] = mapped_column(String, default="pending") # pending, implemented, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

__all__ = [
    "Base", 
    "ProductModel", 
    "OfferModel", 
    "CollectionItemModel", 
    "PendingMatchModel", 
    "PriceAlertModel", 
    "UserModel", 
    "ScraperStatusModel", 
    "BlackcludedItemModel", 
    "PriceHistoryModel", 
    "ScraperExecutionLogModel", 
    "KaizenInsightModel",
    "DOMAIN_VERSION"
]

