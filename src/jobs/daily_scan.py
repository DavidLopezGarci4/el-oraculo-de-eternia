import asyncio
import logging
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

from src.core.logger import setup_logging
from src.scrapers.pipeline import ScrapingPipeline

# Spiders
from src.scrapers.spiders.actiontoys import ActionToysSpider
from src.scrapers.spiders.fantasia import FantasiaSpider
from src.scrapers.spiders.frikiverso import FrikiversoSpider
from src.scrapers.spiders.pixelatoy import PixelatoySpider
from src.scrapers.spiders.dvdstorespain import DVDStoreSpainSpider
from src.scrapers.spiders.electropolis import ElectropolisSpider

async def run_daily_scan(progress_callback=None):
    # Ensure logging is set up
    setup_logging()
    logger = logging.getLogger("daily_scan")
    logger.info("🚀 Starting Daily Oracle Scan...")
    
    # --- AUTOMATIC BACKUP ---
    try:
        import shutil
        import os
        from datetime import datetime, timedelta
        
        backup_dir = "backups"
        db_file = "oraculo.db"
        
        if os.path.exists(db_file):
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_path = f"{backup_dir}/oraculo_{timestamp}.db"
            
            shutil.copy2(db_file, backup_path)
            logger.info(f"🛡️ Backup created: {backup_path}")
            
            # Rotation: Keep last 7 days (or just last 7 files)
            # Simple approach: List all files in backups/, sort by time, delete old ones
            files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".db")]
            files.sort(key=os.path.getmtime)
            
            if len(files) > 7:
                for f_to_del in files[:-7]:
                    os.remove(f_to_del)
                    logger.info(f"🗑️ Rotated old backup: {f_to_del}")
    except Exception as e:
        logger.error(f"⚠️ Backup failed: {e}")
    # ------------------------
    
    # Pass empty list to pipeline init as we are orchestrating manually
    pipeline = ScrapingPipeline([])
    
    # List of Active Spiders
    spiders = [
        ActionToysSpider(),
        FantasiaSpider(),
        FrikiversoSpider(),
        PixelatoySpider(),
        DVDStoreSpainSpider(),
        ElectropolisSpider()
    ]
    
    results = {}
    total_stats = {"found": 0, "new": 0, "errors": 0}
    
    start_time = datetime.now()
    
    # DB Session for Status Updates
    from src.infrastructure.database import SessionLocal
    from src.domain.models import ScraperStatusModel
    db = SessionLocal()

    total_spiders = len(spiders)
    
    for idx, spider in enumerate(spiders):
        logger.info(f"🕸️ Engaging {spider.shop_name}...")
        
        # UI Progress Update (if callback provided)
        progress_val = int((idx / total_spiders) * 100)
        if progress_callback:
            progress_callback(spider.shop_name, progress_val)
            
        # DB Status Update (Running)
        try:
            status_row = db.query(ScraperStatusModel).filter(ScraperStatusModel.spider_name == spider.shop_name).first()
            if not status_row:
                status_row = ScraperStatusModel(spider_name=spider.shop_name)
                db.add(status_row)
            status_row.status = "running"
            status_row.last_update = datetime.now()
            db.commit()
        except Exception:
            db.rollback()

        try:
            # 1. Scrape
            offers = await spider.search("auto")
            
            # 2. Persist
            if offers:
                pipeline.update_database(offers)
                stats = {
                    "items_found": len(offers),
                    "status": "Success"
                }
                total_stats["found"] += len(offers)
            else:
                stats = {"items_found": 0, "status": "Empty"}
            
            # DB Status Update (Completed)
            try:
                status_row.status = "completed"
                status_row.items_scraped = len(offers) if offers else 0
                status_row.last_update = datetime.now()
                db.commit()
            except Exception:
                db.rollback()

            results[spider.shop_name] = stats
            logger.info(f"✅ {spider.shop_name} Complete: {stats}")
            
        except Exception as e:
            logger.error(f"❌ Failed {spider.shop_name}: {e}")
            results[spider.shop_name] = {"error": str(e)}
            total_stats["errors"] += 1
            
            # DB Status Update (Error)
            try:
                status_row.status = "error"
                db.commit()
            except Exception:
                db.rollback()
    
    # Final Callback
    if progress_callback:
        progress_callback("Completado", 100)
    
    db.close()


    duration = datetime.now() - start_time
    logger.info(f"🏁 Daily Scan Complete in {duration}. Total: {total_stats}")
    
    # Optional: Dump report to file
    report_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"📄 Report saved to {report_file}")
    except Exception as e:
        logger.warning(f"Could not save report json: {e}")

if __name__ == "__main__":
    asyncio.run(run_daily_scan())
