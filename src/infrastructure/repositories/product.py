from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from src.infrastructure.repositories.base import BaseRepository
from src.domain.models import ProductModel, OfferModel

class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, db: Session):
        super().__init__(ProductModel, db)

    def get_by_name(self, name: str) -> Optional[ProductModel]:
        return self.db.query(ProductModel).filter(ProductModel.name == name).first()

    def get_offer_by_url(self, url: str) -> Optional[OfferModel]:
        return self.db.query(OfferModel).filter(OfferModel.url == url).first()
    
    def add_offer(self, product: ProductModel, offer_data: dict) -> tuple[OfferModel, Optional[float]]:
        from src.domain.models import PriceHistoryModel
        
        target_url = offer_data["url"]
        existing_offer = next((o for o in product.offers if o.url == target_url), None)
        current_price = float(offer_data["price"])
        alert_discount = None
        
        # --- EAN KAIZEN: Update product EAN if missing ---
        if not product.ean and offer_data.get("ean"):
             product.ean = offer_data["ean"]
             self.db.add(product)
        
        if existing_offer:
            # Check for Price Changes
            if abs(existing_offer.price - current_price) > 0.01:
                 ph = PriceHistoryModel(offer_id=existing_offer.id, price=current_price)
                 self.db.add(ph)

            # Check for Alert Condition (New Low + Significant Discount)
            # Only alert if it's a DROPPING price that sets a new record low (to prevent spam on every scan)
            if existing_offer.min_price > 0 and current_price < existing_offer.min_price:
                 if existing_offer.max_price > 0:
                     discount = 1.0 - (current_price / existing_offer.max_price)
                     if discount >= 0.20:
                         alert_discount = discount
                         # --- KAIZEN: Nuclear Anomaly Detection (Phase 8) ---
                         if discount >= 0.50:
                             logger.critical(f"🚀 NUCLEAR DEAL DETECTED: {product.name} at {current_price}€ (-{discount*100:.0f}%)")
                             # We'll mark this for special handling in the notifier
                             offer_data["is_nuclear"] = True 

            # Update Stats
            if existing_offer.min_price == 0 or current_price < existing_offer.min_price:
                existing_offer.min_price = current_price
            
            if current_price > existing_offer.max_price:
                existing_offer.max_price = current_price
                
            existing_offer.price = current_price
            existing_offer.is_available = offer_data["is_available"]
            existing_offer.last_seen = datetime.utcnow()
            
            self.db.add(existing_offer)
            self.db.commit()
            self.db.refresh(existing_offer)
            return existing_offer, alert_discount
        else:
            # Create new Offer
            new_offer = OfferModel(
                product_id=product.id,
                shop_name=offer_data["shop_name"],
                price=current_price,
                currency=offer_data.get("currency", "EUR"),
                url=offer_data["url"],
                is_available=offer_data["is_available"],
                min_price=current_price,
                max_price=current_price
            )
            self.db.add(new_offer)
            self.db.flush() 
            
            # Initial History
            ph = PriceHistoryModel(offer_id=new_offer.id, price=current_price)
            self.db.add(ph)
            
            self.db.commit()
            self.db.refresh(new_offer)
            return new_offer, None

    def get_active_deals(self, min_discount: float = 0.20, max_original_price: float = None):
        """
        Find offers where current price is lower than max_price by at least min_discount.
        Returns list of (Product, Offer, discount_percent) sorted by discount.
        """
        query = self.db.query(OfferModel).join(ProductModel).filter(
            OfferModel.is_available == True,
            OfferModel.max_price > 0,
            OfferModel.price < (OfferModel.max_price * (1 - min_discount))
        )
        
        if max_original_price is not None:
             query = query.filter(OfferModel.max_price <= max_original_price)
             
        offers = query.all()
        
        results = []
        for o in offers:
            discount = 1 - (o.price / o.max_price)
            results.append((o.product, o, discount))
            # Sort by discount desc
        results.sort(key=lambda x: x[2], reverse=True)
        return results
