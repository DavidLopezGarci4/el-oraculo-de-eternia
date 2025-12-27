import asyncio
import logging
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

from src.core.logger import setup_logging
from src.scrapers.pipeline import ScrapingPipeline

# New Refactored Scrapers
from src.infrastructure.scrapers.action_toys_scraper import ActionToysScraper
from src.infrastructure.scrapers.fantasia_scraper import FantasiaScraper
from src.infrastructure.scrapers.frikiverso_scraper import FrikiversoScraper
from src.infrastructure.scrapers.pixelatoy_scraper import PixelatoyScraper
from src.infrastructure.scrapers.electropolis_scraper import ElectropolisScraper

async def run_daily_scan(progress_callback=None):
    # Ensure logging is set up
    setup_logging()
    logger = logging.getLogger("daily_scan")
    logger.info("🚀 Starting Daily Oracle Scan (Refactored Loop)...")
    
    # --- AUTOMATIC BACKUP ---
    try:
        import shutil
        import os
        
        backup_dir = "backups"
        db_file = "oraculo.db"
        
        if os.path.exists(db_file):
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_path = f"{backup_dir}/oraculo_{timestamp}.db"
            
            shutil.copy2(db_file, backup_path)
            logger.info(f"🛡️ Backup created: {backup_path}")
            
            # Rotation: Keep last 7 items
            files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".db")]
            files.sort(key=os.path.getmtime)
            
            if len(files) > 7:
                for f_to_del in files[:-7]:
                    os.remove(f_to_del)
                    logger.info(f"🗑️ Rotated old backup: {f_to_del}")
    except Exception as e:
        logger.error(f"⚠️ Backup failed: {e}")
    # ------------------------
    
    # --- ARGUMENT PARSING ---
    import argparse
    parser = argparse.ArgumentParser(description="Oracle Scraper Runner")
    parser.add_argument("--shops", nargs="*", help="Specific shops to scrape (e.g. electropolis fantasia)")
    parser.add_argument("--random-delay", type=int, default=0, help="Wait up to X minutes before starting (jitter)")
    parser.add_argument("--deep-harvest", action="store_true", help="Visit individual product pages for EAN/GTIN extraction")
    args, unknown = parser.parse_known_args()
    
    # --- STAGGERED START (KAIZEN) ---
    if args.random_delay > 0:
        import random
        wait_mins = random.uniform(0, args.random_delay)
        logger.info(f"⏳ Kaizen: Staggered start active. Waiting {wait_mins:.2f} minutes before engaging robots...")
        await asyncio.sleep(wait_mins * 60)
    
    # --- PID MANAGEMENT ---
    pid = os.getpid()
    pid_file = ".scan_pid"
    with open(pid_file, "w") as f:
        f.write(str(pid))
        
    try:
        # PHASE 12: Ensure database schema is up to date before scanning
        try:
            from src.infrastructure.universal_migrator import migrate
            logger.info("🔧 Synchronizing database schema (Universal Migrator)...")
            migrate()
        except Exception as e:
            logger.warning(f"⚠️ Migration pre-check failed: {e}")

        # Initialize Pipeline
        pipeline = ScrapingPipeline([])
        
        # List of Scrapers
        all_scrapers = [
            ActionToysScraper(),
            FantasiaScraper(),
            FrikiversoScraper(),
            PixelatoyScraper(),
            ElectropolisScraper()
        ]
        
        # Filter Scrapers
        scrapers = []
        if args.shops:
            target_shops = [s.lower() for s in args.shops]
            logger.info(f"🎯 Target Execution: {target_shops}")
            for s in all_scrapers:
                if any(t in s.spider_name.lower() for t in target_shops):
                    scrapers.append(s)
        else:
            scrapers = all_scrapers
            
    except Exception as e:
        logger.error(f"Failed to initialize scrapers: {e}")
        scrapers = []
    
    results = {}
    total_stats = {"found": 0, "new": 0, "errors": 0}
    start_time = datetime.now()
    
    # DB Session for Status Updates
    from src.infrastructure.database import SessionLocal
    from src.domain.models import ScraperStatusModel
    from src.core.audit_logger import AuditLogger
    
    db = SessionLocal()
    audit = AuditLogger(db)

    total_scrapers = len(scrapers)
    
    # User-Agent List for Rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
    import random

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for idx, scraper in enumerate(scrapers):
            # Check for Stop Signal
            if os.path.exists(".stop_scan"):
                logger.warning("🛑 Stop Signal Detected. Aborting scan sequence.")
                try:
                    os.remove(".stop_scan")
                except:
                    pass
                break
                
            logger.info(f"🕸️ Engaging {scraper.spider_name}...")
            
            # Select Random User-Agent
            current_ua = random.choice(user_agents)
            logger.info(f"🎭 Using User-Agent: {current_ua[:50]}...")
            
            # Create Isolated Context
            context = await browser.new_context(user_agent=current_ua)
            
            # Inject Audit Logger
            scraper.audit_logger = audit

            # UI Progress Update
            progress_val = int((idx / total_scrapers) * 100)
            if progress_callback:
                progress_callback(scraper.spider_name, progress_val)
                
            # DB Status Update (Running)
            try:
                status_row = db.query(ScraperStatusModel).filter(ScraperStatusModel.spider_name == scraper.spider_name).first()
                if not status_row:
                    status_row = ScraperStatusModel(spider_name=scraper.spider_name)
                    db.add(status_row)
                status_row.status = "running"
                status_row.progress = progress_val
                status_row.last_update = datetime.now()
                db.commit()
            except Exception:
                db.rollback()

            # Create Execution Log Entry
            from src.domain.models import ScraperExecutionLogModel
            log_entry = ScraperExecutionLogModel(
                spider_name=scraper.spider_name,
                status="running",
                start_time=datetime.now(),
                trigger_type="manual" if args.shops else "scheduled" # infer based on args
            )
            try:
                db.add(log_entry)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to create execution log: {e}")
                db.rollback()

            try:
                # 1. Scrape
                offers = await scraper.run(context)
                
                # PHASE 19: Health & Block Alerts (Sentinel)
                from src.core.notifier import NotifierService
                notifier = NotifierService()
                if not offers:
                    if getattr(scraper, 'blocked', False):
                        logger.error(f"[{scraper.spider_name}] 🚫 Blocked by anti-bot measures.")
                        msg = f"🚫 **DESTIERRO DETECTADO**\n\nEl Oráculo ha sido bloqueado por **{scraper.spider_name}**. Se requieren medidas de evasión táctica."
                        await notifier.send_message(msg)
                        log_entry.status = "blocked"
                        log_entry.error_message = "Anti-bot block detected"
                    else:
                        logger.warning(f"[{scraper.spider_name}] ⚠️ Empty scan results.")
                        # Alert if this is a shop that usually has items (most of them)
                        msg = f"⚠️ **SALUD COMPROMETIDA**\n\nEl scraper de **{scraper.spider_name}** ha devuelto 0 resultados. Podría ser un cambio de estructura HTML o falta de stock real."
                        await notifier.send_message(msg)
                        log_entry.status = "empty_warning"
                
                # 2. Persist
                if offers:
                    # PHASE 10: Deep Harvest (Precision)
                    if args.deep_harvest and offers:
                        logger.info(f"🔍 [{scraper.spider_name}] Deep Harvest active. Refining {len(offers)} items...")
                        for item in offers:
                            # Visit detail page if EAN is missing and we want precision
                            if not getattr(item, 'ean', None):
                                # Ensure the scraper has a _scrape_detail method
                                if hasattr(scraper, '_scrape_detail') and callable(getattr(scraper, '_scrape_detail')):
                                    # Create a temporary page for detail scraping to avoid interference
                                    detail_page = await context.new_page()
                                    try:
                                        detail_data = await scraper._scrape_detail(detail_page, item.url)
                                        if detail_data and detail_data.get('ean'):
                                            item.ean = detail_data['ean']
                                            logger.info(f"   🎯 Fingerprint found for '{item.product_name}': {item.ean}")
                                    finally:
                                        await detail_page.close()
                                        
                                    await asyncio.sleep(random.uniform(1.0, 3.0)) # Jitter between detail pages
                                else:
                                    logger.warning(f"⚠️ Scraper {scraper.spider_name} does not implement _scrape_detail for deep harvest.")

                    # Update Database
                    pipeline.update_database(offers)
                    stats = {
                        "items_found": len(offers),
                        "status": "Success"
                    }
                    total_stats["found"] += len(offers)
                    
                    # Log Update Success
                    log_entry.items_found = len(offers)
                    log_entry.status = "success"
                else:
                    stats = {"items_found": 0, "status": "Empty"}
                    log_entry.status = "success_empty"
                
                # DB Status Update (Completed)
                try:
                    status_row.status = "completed"
                    status_row.items_scraped = len(offers) if offers else 0
                    status_row.last_update = datetime.now()
                    
                    # Finalize Log
                    log_entry.end_time = datetime.now()
                    db.commit()
                except Exception:
                    db.rollback()

                results[scraper.spider_name] = stats
                logger.info(f"✅ {scraper.spider_name} Complete: {stats}")
                
            except Exception as e:
                logger.error(f"❌ Failed {scraper.spider_name}: {e}")
                results[scraper.spider_name] = {"error": str(e)}
                total_stats["errors"] += 1
                
                # DB Status Update (Error)
                try:
                    status_row.status = "error"
                    
                    # Finalize Log Error
                    log_entry.status = "error"
                    log_entry.error_message = str(e)[:500]
                    log_entry.end_time = datetime.now()
                    
                    db.commit()
                except Exception:
                    db.rollback()
            finally:
                await context.close()
        
        await browser.close()
    
    # Final Callback
    if progress_callback:
        progress_callback("Completado", 100)
    
    db.close()

    # PHASE 18: Create Database Vault (Safe Backup)
    try:
        from src.core.backup_manager import BackupManager
        from src.infrastructure.database import SessionLocal
        
        logger.info("🏰 Sealing the Data Vault (Database Backup)...")
        backup_db = SessionLocal()
        bm = BackupManager()
        backup_path = bm.create_database_backup(backup_db)
        if backup_path:
            logger.info(f"🛡️ Vault sealed at: {backup_path}")
        backup_db.close()
    except Exception as e:
        logger.error(f"⚠️ Failed to seal Data Vault: {e}")

    duration = datetime.now() - start_time
    logger.info(f"🏁 Daily Scan Complete in {duration}. Total: {total_stats}")
    
    # Dump report to file
    report_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        os.makedirs("logs", exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"📄 Report saved to {report_file}")
    except Exception as e:
        logger.warning(f"Could not save report json: {e}")
        
    # Cleanup PID
    if os.path.exists(pid_file):
        os.remove(pid_file)

if __name__ == "__main__":
    try:
        # if sys.platform == "win32":
        #    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(run_daily_scan())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # --- EMERGENCY DB LOGGING ---
        try:
            from src.infrastructure.database import SessionLocal
            from src.domain.models import ScraperExecutionLogModel
            from datetime import datetime
            
            db_err = SessionLocal()
            log_err = ScraperExecutionLogModel(
                spider_name="Global_System", # Special name for script-wide errors
                status="critical_failure",
                start_time=datetime.now(),
                end_time=datetime.now(),
                trigger_type="scheduled", # Assume scheduled if crashing
                error_message=f"CRITICAL SCRIPT FAILURE: {str(e)}\n\n{traceback.format_exc()}"[:2000] # Truncate for safety
            )
            db_err.add(log_err)
            db_err.commit()
            db_err.close()
            print(">> CRITICAL ERROR LOGGED TO DB")
        except Exception as db_ex:
            print(f">> FAILED TO LOG TO DB: {db_ex}")
        # ----------------------------
        
        # input("Press Enter to exit (Debug Mode)...")
