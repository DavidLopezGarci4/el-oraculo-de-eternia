import sys
from pathlib import Path
from sqlalchemy import text
import logging

# Add project root
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

from src.infrastructure.database import SessionLocal, engine
from src.domain.models import OfferModel, PendingMatchModel, PriceHistoryModel

def reset_hunter_data():
    setup_logging()
    logger = logging.getLogger("reset_hunter")
    logger.info("🧨 Initiating Hunter Data Purge...")
    
    db = SessionLocal()
    try:
        # 1. Delete Price History (Child of Offers)
        num_history = db.query(PriceHistoryModel).delete()
        logger.info(f"🗑️ Deleted {num_history} price history records.")
        
        # 2. Delete Offers
        num_offers = db.query(OfferModel).delete()
        logger.info(f"🗑️ Deleted {num_offers} active offers.")
        
        # 3. Delete Pending Matches
        num_pending = db.query(PendingMatchModel).delete()
        logger.info(f"🗑️ Deleted {num_pending} pending matches.")
        
        # 4. Vacuum / Optimize (Optional, good for SQLite)
        # db.execute(text("VACUUM")) 
        
        db.commit()
        logger.info("✨ Hunter Data successfully wiped. Ready for fresh scan.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during purge: {e}")
    finally:
        db.close()

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    reset_hunter_data()
