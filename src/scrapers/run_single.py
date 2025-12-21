import asyncio
import sys
from src.scrapers.pipeline import ScrapingPipeline
from src.scrapers.spiders.actiontoys import ActionToysSpider
from src.scrapers.spiders.fantasia import FantasiaSpider
# from src.scrapers.spiders.amazon import AmazonSpider
# from src.scrapers.spiders.kidinn import KidInnSpider
from src.core.logger import logger

async def run_spider(spider_name: str):
    logger.info(f"🚀 Launching spider: {spider_name}")
    
    spiders = []
    if spider_name.lower() == "actiontoys":
        spiders.append(ActionToysSpider())
    elif spider_name.lower() == "fantasia":
        spiders.append(FantasiaSpider())
    elif spider_name.lower() == "electropolis":
        from src.scrapers.spiders.electropolis import ElectropolisSpider
        spiders.append(ElectropolisSpider())
    # elif spider_name.lower() == "amazon":
    #     spiders.append(AmazonSpider())
    else:
        logger.error(f"Unknown spider: {spider_name}")
        return

    # Scraper Status - Init
    from src.infrastructure.database import SessionLocal
    from src.domain.models import ScraperStatusModel
    import datetime
    
    db = SessionLocal()
    status_row = db.query(ScraperStatusModel).filter(ScraperStatusModel.spider_name == spider_name).first()
    if not status_row:
        status_row = ScraperStatusModel(spider_name=spider_name)
        db.add(status_row)
    
    status_row.status = "running"
    status_row.start_time = datetime.datetime.utcnow()
    status_row.items_scraped = 0
    db.commit()

    try:
        pipeline = ScrapingPipeline(spiders)
        
        # We use "auto" to let the spider decide the best scraping strategy
        results = await pipeline.run_product_search("auto")
        
        logger.info(f"💾 Persisting {len(results)} offers to database...")
        pipeline.update_database(results)
        
        status_row.status = "completed"
        status_row.items_scraped = len(results)
        status_row.end_time = datetime.datetime.utcnow()
        db.commit()
        
        logger.success("✅ Cycle complete.")
    except Exception as e:
        status_row.status = "error"
        status_row.end_time = datetime.datetime.utcnow()
        db.commit()
        logger.error(f"❌ Scraper failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/scrapers/run_single.py <spider_name>")
    else:
        asyncio.run(run_spider(sys.argv[1]))
