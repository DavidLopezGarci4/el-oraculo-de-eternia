import sys
import asyncio
import json
# Import Spiders
from src.scrapers.spiders.frikiverso import FrikiversoSpider
from src.scrapers.spiders.fantasia import FantasiaSpider
from src.scrapers.spiders.pixelatoy import PixelatoySpider
from src.scrapers.spiders.electropolis import ElectropolisSpider
from src.scrapers.spiders.dvdstorespain import DVDStoreSpainSpider
from src.core.logger import logger

async def profile(spider_name):
    spider = None
    if spider_name.lower() == "frikiverso":
        spider = FrikiversoSpider()
    elif spider_name.lower() == "fantasia":
        spider = FantasiaSpider()
    elif spider_name.lower() == "pixelatoy":
        spider = PixelatoySpider()
    elif spider_name.lower() == "electropolis":
        spider = ElectropolisSpider()
    elif spider_name.lower() == "dvdstorespain":
        spider = DVDStoreSpainSpider()
    else:
        logger.error(f"❌ Unknown spider: {spider_name}")
        return

    logger.info(f"🔮 Profiling {spider.shop_name} (Dry Run)...")
    try:
        offers = await spider.search("auto")
        
        # Extract ONLY titles as requested
        titles = sorted([o.product_name for o in offers])
        
        filename = f"data/profile_{spider_name}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(titles, f, indent=2, ensure_ascii=False)
            
        logger.info(f"✅ Simulation Complete. Saved {len(titles)} titles to {filename}")
        logger.info("ℹ️ No changes were made to the database.")
        
    except Exception as e:
        logger.error(f"❌ Error during profiling: {e}")

if __name__ == "__main__":
    # Default to frikiverso if not argument provided
    target = sys.argv[1] if len(sys.argv) > 1 else "frikiverso"
    asyncio.run(profile(target))
