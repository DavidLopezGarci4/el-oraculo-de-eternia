import asyncio
from typing import List
from loguru import logger
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.domain.schemas import Product
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
                    saved_o, _ = repo.add_offer(existing_offer.product, {
                        "shop_name": offer.shop_name,
                        "price": offer.price,
                        "currency": offer.currency, 
                        "url": str(offer.url),
                        "is_available": offer.is_available
                    })
                    
                    # Centinela Check
                    from src.core.notifier import NotifierService
                    NotifierService().check_price_alerts_sync(db, existing_offer.product, saved_o)
                    continue # Skip SmartMatch
                
                # Iterate all DB products to find best
                for p in all_products:
                    is_match, score, reason = matcher.match(
                        p.name, 
                        offer.product_name, 
                        str(offer.url),
                        db_ean=p.ean,
                        scraped_ean=getattr(offer, 'ean', None)
                    )
                    
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
                    
                    # Centinela Check (Fase 15)
                    from src.core.notifier import NotifierService
                    NotifierService().check_price_alerts_sync(db, best_match_product, saved_offer)
                else:
                    logger.info(f"⏳ No Match Found: '{offer.product_name}' (Top Score: {best_match_score:.2f}) -> Routing to Purgatory")
                    
                    # Check blacklist
                    from src.domain.models import BlackcludedItemModel
                    is_blacklisted = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.url == str(offer.url)).first()
                    if is_blacklisted:
                        logger.warning(f"🚫 Ignored (Blacklist): {offer.product_name}")
                        continue
                        
                    # Check if already exists in Pending
                    from src.domain.models import PendingMatchModel
                    existing = db.query(PendingMatchModel).filter(PendingMatchModel.url == str(offer.url)).first()
                    if not existing:
                        # Defensive instantiation: Filter out keys that the model doesn't support
                        # This is the ULTIMATE defensive pattern against schema mismatches
                        all_data = {
                            "scraped_name": offer.product_name,
                            "price": offer.price,
                            "currency": getattr(offer, 'currency', 'EUR'),
                            "url": str(offer.url),
                            "shop_name": offer.shop_name,
                            "image_url": offer.image_url if hasattr(offer, 'image_url') else None,
                            "ean": getattr(offer, 'ean', None)
                        }
                        
                        # Filter: Keep only keys present in the model class
                        from sqlalchemy.inspect import inspect
                        try:
                            mapper = inspect(PendingMatchModel)
                            allowed_keys = {c.key for c in mapper.attrs}
                            pending_data = {k: v for k, v in all_data.items() if k in allowed_keys}
                        except:
                            # Fallback if inspection fails
                            pending_data = {k: v for k, v in all_data.items() if hasattr(PendingMatchModel, k)}

                        try:
                            pending = PendingMatchModel(**pending_data)
                            db.add(pending)
                            db.commit()
                        except TypeError as e:
                            # Level 4 Safeguard: If instantiation fails due to keyword args, 
                            # try a safe fallback without extra metadata
                            logger.warning(f"⚠️ Model instantiation failed: {e}. Retrying with safe subset.")
                            db.rollback()
                            safe_data = {k: v for k, v in pending_data.items() if k not in ['ean', 'image_url']}
                            pending = PendingMatchModel(**safe_data)
                            db.add(pending)
                            db.commit()
                        except Exception as e:
                            logger.error(f"❌ Critical DB failure in Purgatory routing: {e}")
                            db.rollback()
                        
                        # LOG HISTORY: PURGATORY
                        try:
                            from src.domain.models import OfferHistoryModel
                            history = OfferHistoryModel(
                                offer_url=str(offer.url),
                                product_name=offer.product_name,
                                shop_name=offer.shop_name,
                                price=offer.price,
                                action_type="PURGATORY",
                                details=f"Match score too low ({best_match_score:.2f}). Moved to Purgatory."
                            )
                            db.add(history)
                            db.commit()
                        except: pass

        finally:
            db.close()
