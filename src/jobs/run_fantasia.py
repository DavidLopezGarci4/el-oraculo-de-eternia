import asyncio
from src.scrapers.spiders.fantasia import FantasiaSpider
from src.scrapers.pipeline import ScrapingPipeline
from src.infrastructure.database import SessionLocal
from src.core.logger import logger

async def run_fantasia_job():
    logger.info("🚀 Starting Fantasia Job...")
    
    # 1. Scrape
    spider = FantasiaSpider()
    logger.info("🕷️ Spider Initialized. Running search('auto')...")
    offers = await spider.search("auto")
    
    logger.info(f"📦 Collected {len(offers)} offers. Starting pipeline...")
    
    # 2. Ingest
    db = SessionLocal()
    try:
        pipeline = ScrapingPipeline(db)
        pipeline.update_database(offers)
        
        logger.info("✅ Job Complete: Database updated.")
        # logger.info(f"📊 Stats: Processed={stats['processed']}, Matches={stats['matches']}, Pending={stats['pending']}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_fantasia_job())
