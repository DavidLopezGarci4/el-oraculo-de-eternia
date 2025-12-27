import json
import os
import sys
import logging
from pathlib import Path
from sqlalchemy import text
from src.infrastructure.database import SessionLocal, engine
from src.domain.models import (
    Base, ProductModel, OfferModel, PendingMatchModel, OfferHistoryModel,
    UserModel, PriceAlertModel, CollectionItemModel, BlackcludedItemModel,
    KaizenInsightModel, ScraperExecutionLogModel, PriceHistoryModel
)

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger("restore_tool")

def restore_from_vault(file_path: str):
    """
    Restores the database from a JSON vault file.
    WARNING: This will clear current tables before restoring!
    Now supports sequences sync for Postgres.
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return

    logger.info(f"🛡️ Preparing to restore from: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            vault = json.load(f)
        
        metadata = vault.get("metadata", {})
        data = vault.get("data", {})
        
        logger.info(f"📅 Backup Timestamp: {metadata.get('timestamp')}")
        
        db = SessionLocal()
        
        try:
            # 1. DELETE CURRENT DATA (Reverse order of dependencies)
            logger.warning("🌪️ Clearing existing data for a clean restore...")
            # Deleting in order that respects FKs
            db.query(PriceHistoryModel).delete()
            db.query(PriceAlertModel).delete()
            db.query(CollectionItemModel).delete()
            db.query(OfferHistoryModel).delete()
            db.query(OfferModel).delete()
            db.query(PendingMatchModel).delete()
            db.query(ProductModel).delete()
            db.query(BlackcludedItemModel).delete()
            db.query(KaizenInsightModel).delete()
            db.query(ScraperExecutionLogModel).delete()
            db.query(UserModel).delete()
            db.commit()
            
            # 2. RESTORE DATA (Order of dependencies)
            # Users
            if "users" in data:
                logger.info(f"👤 Restoring {len(data['users'])} users...")
                for d in data["users"]: db.add(UserModel(**d))
            
            # Products
            logger.info(f"📦 Restoring {len(data['products'])} products...")
            for d in data["products"]: db.add(ProductModel(**d))
            db.flush() 

            # Rest of tables
            table_map = {
                "pending_matches": PendingMatchModel,
                "offers": OfferModel,
                "offer_history": OfferHistoryModel,
                "price_alerts": PriceAlertModel,
                "collection_items": CollectionItemModel,
                "blackcluded_items": BlackcludedItemModel,
                "kaizen_insights": KaizenInsightModel,
                "scraper_execution_logs": ScraperExecutionLogModel,
                "price_history": PriceHistoryModel
            }

            for key, model in table_map.items():
                if key in data:
                    logger.info(f"🔄 Restoring {len(data[key])} {key}...")
                    for d in data[key]: db.add(model(**d))
                
            db.commit()
            
            # 3. SYNC SEQUENCES (CRITICAL FOR POSTGRES/SUPABASE)
            if "postgresql" in str(engine.url):
                logger.info("⚡ Synchronizing Postgres ID sequences...")
                for table in ["users", "products", "offers", "pending_matches", "offer_history", 
                              "price_alerts", "collection_items", "blackcluded_items", 
                              "kaizen_insights", "scraper_execution_logs", "price_history"]:
                    db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"))
                db.commit()

            logger.info("✅ RESTORE COMPLETE. Eternia has been restored and sequences synced.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Restore failed during DB operations: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Failed to read vault file: {e}")

def list_available_backups():
    path = Path("backups/database")
    if not path.exists():
        logger.info("No backups found.")
        return []
    
    files = sorted(list(path.glob("*.json")), key=os.path.getmtime, reverse=True)
    for i, f in enumerate(files):
        logger.info(f"[{i}] {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    return files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Eternia Restore Tool")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--file", type=str, help="Absolute path to vault file to restore")
    args = parser.parse_args()
    
    if args.list:
        list_available_backups()
    elif args.file:
        print("\n" + "!"*40)
        print("CRITICAL WARNING: This will DELETE ALL current data")
        print("and replace it with the backup content.")
        print("!"*40 + "\n")
        confirm = input("Are you ABSOLUTELY sure? (yes/no): ")
        if confirm.lower() == "yes":
            restore_from_vault(args.file)
        else:
            print("Restore aborted.")
    else:
        # Interactive mode if no args
        backups = list_available_backups()
        if backups:
            choice = input("\nEnter index to restore (or 'q' to quit): ")
            if choice.isdigit() and int(choice) < len(backups):
                confirm = input(f"Restore {backups[int(choice)].name}? (yes/no): ")
                if confirm.lower() == "yes":
                    restore_from_vault(str(backups[int(choice)]))
            else:
                print("Exiting.")
