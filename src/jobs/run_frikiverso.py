import asyncio
from src.scrapers.spiders.frikiverso import FrikiversoSpider
from src.scrapers.pipeline import ScrapingPipeline
from src.infrastructure.database import SessionLocal
from src.core.logger import logger

async def run_frikiverso_job():
    logger.info("🚀 Starting Frikiverso Job (Auto Mode)...")
    
    # 1. Scrape
    spider = FrikiversoSpider()
    offers = await spider.search("auto")
    
    logger.info(f"📦 Collected {len(offers)} offers. Starting pipeline...")
    
    # 2. Ingest
    db = SessionLocal()
    try:
        pipeline = ScrapingPipeline(db)
        pipeline.update_database(offers)
        
        logger.info("✅ Job Complete: Database updated.")
        
    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_frikiverso_job())
