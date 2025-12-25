import asyncio
from typing import List
from loguru import logger
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.domain.schemas import Product
from src.domain.models import PendingMatchModel, BlackcludedItemModel
from src.infrastructure.repositories.product import ProductRepository
from sqlalchemy.orm import Session
from src.infrastructure.database import SessionLocal

class ScrapingPipeline:
    def __init__(self, spiders: List[BaseSpider]):
        self.spiders = spiders

    async def run_product_search(self, product_name: str) -> List[ScrapedOffer]:
        """
        Runs all spiders in parallel for a given product name.
        """
        logger.info(f"Pipeline: Searching for '{product_name}' across {len(self.spiders)} spiders.")
        
        tasks = [spider.search(product_name) for spider in self.spiders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_offers = []
        for spider, res in zip(self.spiders, results):
            if isinstance(res, Exception):
                logger.error(f"Spider {spider.shop_name} failed for '{product_name}': {res}")
            else:
                logger.info(f"Spider {spider.shop_name} found {len(res)} offers.")
                all_offers.extend(res)
                
        return all_offers

    def clean_product_name(self, name: str) -> str:
        """
        Normalizes product names for better fuzzy matching.
        """
        import re
        n = name.lower()
        # Specific fix for "Sun-Man" -> "Sun Man" to handle hyphenated names
        n = n.replace("-", " ")
        
        remove_list = [
            "masters of the universe", "motu", "origins", 
            "figura", "figure", "action", "mattel", "14 cm", "14cm"
        ]
        for w in remove_list:
            n = n.replace(w, "")
        
        # Remove special chars but keep spaces
        n = re.sub(r'[^a-zA-Z0-9\s]', '', n)
        return " ".join(n.split())

    def update_database(self, offers: List[ScrapedOffer]):
        """
        Persists found offers to the database using SmartMatcher.
        """
        db: Session = SessionLocal()
        from src.core.matching import SmartMatcher
        
        matcher = SmartMatcher()
        repo = ProductRepository(db)
        
        try:
            # Pre-fetch all product names/IDs
            all_products = repo.get_all(limit=5000)
            
            # Note: We must compare against ALL products to find the BEST match.
            # SmartMatcher is fast enough for 5000 items (simple set operations).
            
            for offer in offers:
                best_match_product = None
                best_match_score = 0.0
                
                # Check 1: Does this offer satisfy "Already Linked" logic?
                # "Una vez asociado ... ha de quedar inamovible"
                # If we have an existing Offer with this URL, we MUST use its product_id, ignoring SmartMatcher.
                existing_offer = repo.get_offer_by_url(str(offer.url))
                
                if existing_offer:
                    # It's an update to an existing link
                    logger.info(f"🔗 Known Link: '{offer.product_name}' -> '{existing_offer.product.name}' (Price Update)")
                    repo.add_offer(existing_offer.product, {
                        "shop_name": offer.shop_name,
                        "price": offer.price,
                        "currency": offer.currency, 
                        "url": str(offer.url),
                        "is_available": offer.is_available
                    })
                    continue # Skip SmartMatch
                
                # Iterate all DB products to find best
                for p in all_products:
                    is_match, score, reason = matcher.match(p.name, offer.product_name, str(offer.url))
                    
                    if is_match and score > best_match_score:
                        best_match_score = score
                        best_match_product = p
                        
                        if score >= 0.99:
                             break
                
                if best_match_product and best_match_score >= 0.7:  # Strict Threshold
                    logger.info(f"✅ SmartMatch: '{offer.product_name}' -> '{best_match_product.name}' (Score: {best_match_score:.2f})")
                    
                    saved_offer, alert_discount = repo.add_offer(best_match_product, {
                        "shop_name": offer.shop_name,
                        "price": offer.price,
                        "currency": offer.currency, 
                        "url": str(offer.url),
                        "is_available": offer.is_available
                    })
                    
                    if alert_discount:
                        from src.core.notifier import NotifierService
                        notifier = NotifierService()
                        notifier.send_deal_alert_sync(best_match_product, saved_offer, alert_discount)
                else:
                    logger.info(f"⏳ No Match Found: '{offer.product_name}' (Top Score: {best_match_score:.2f}) -> Routing to Purgatory")
                    
                    # Check blacklist
                    is_blacklisted = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.url == str(offer.url)).first()
                    if is_blacklisted:
                        logger.warning(f"🚫 Ignored (Blacklist): {offer.product_name}")
                        continue
                        
                    # Check if already exists in Pending
                    existing = db.query(PendingMatchModel).filter(PendingMatchModel.url == str(offer.url)).first()
                    if not existing:
                        pending = PendingMatchModel(
                            scraped_name=offer.product_name,
                            price=offer.price,
                            currency=offer.currency,
                            url=str(offer.url),
                            shop_name=offer.shop_name,
                            image_url=offer.image_url if hasattr(offer, 'image_url') else None 
                        )
                        db.add(pending)
                        db.commit()

        finally:
            db.close()
