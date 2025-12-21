import json
import asyncio
from src.scrapers.base import ScrapedOffer
from src.scrapers.pipeline import ScrapingPipeline
from src.core.logger import logger

INPUT_FILE = "data/actiontoys_eval.json"

def ingest_data():
    logger.info(f"Loading data from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {INPUT_FILE}")
        return

    offers = []
    for item in data:
        try:
            # Ensure price is float
            price = float(item.get("price", 0.0))
            if price == 0.0: continue
            
            offer = ScrapedOffer(
                product_name=item["product_name"],
                price=price,
                currency=item.get("currency", "EUR"),
                url=item["url"],
                shop_name=item.get("shop_name", "ActionToys"),
                is_available=item.get("is_available", True),
                image_url=item.get("image_url")
            )
            offers.append(offer)
        except Exception as e:
            logger.warning(f"Skipping invalid item: {item.get('product_name')} - {e}")

    logger.info(f"Loaded {len(offers)} valid offers. Starting Database Update...")
    
    # Initialize Pipeline with empty spiders list correctly (BaseSpider abstract might complain if we tried to mock it too hard, 
    # but Pipeline only stores the list, doesn't validate types deeply in __init__)
    pipeline = ScrapingPipeline(spiders=[])
    
    # Pipeline.update_database is synchronous? 
    # Checking code... update_database definition is def update_database(self, offers: List[ScrapedOffer]): (Sync)
    pipeline.update_database(offers)
    
    logger.info("Ingestion Complete.")

if __name__ == "__main__":
    ingest_data()
