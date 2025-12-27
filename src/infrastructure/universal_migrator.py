import logging
from sqlalchemy import text, inspect
from src.infrastructure.database import engine
from src.domain.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("universal_migrator")

def migrate():
    """
    Intelligently synchronizes DB schema for both SQLite and Postgres.
    Does NOT use Alembic to maintain project simplicity but ensures reliability.
    """
    logger.info("Starting Universal Migration...")
    
    inspector = inspect(engine)
    
    # Tables to check
    tables = inspector.get_table_names()
    
    # 1. Ensure new tables exist (price_alerts)
    # create_all is safe, it only creates tables that don't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Checked/Created core tables (including OfferHistory).")

    # 2. Check for missing columns in existing tables
    with engine.connect() as conn:
        # --- Table: products ---
        columns_products = [c['name'] for c in inspector.get_columns("products")]
        if "ean" not in columns_products:
            logger.info("Adding 'ean' to products table...")
            try:
                conn.execute(text("ALTER TABLE products ADD COLUMN ean VARCHAR(50) UNIQUE"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add ean: {e}")

        # --- Table: offers ---
        columns_offers = [c['name'] for c in inspector.get_columns("offers")]
        if "currency" not in columns_offers:
            logger.info("Adding 'currency' to offers table...")
            conn.execute(text("ALTER TABLE offers ADD COLUMN currency VARCHAR(10) DEFAULT 'EUR'"))
            conn.commit()
            
        if "min_price" not in columns_offers:
            logger.info("Adding 'min_price' to offers table...")
            conn.execute(text("ALTER TABLE offers ADD COLUMN min_price FLOAT DEFAULT 0.0"))
            conn.commit()

        if "max_price" not in columns_offers:
            logger.info("Adding 'max_price' to offers table...")
            conn.execute(text("ALTER TABLE offers ADD COLUMN max_price FLOAT DEFAULT 0.0"))
            conn.commit()

        # --- Table: pending_matches ---
        columns_pending = [c['name'] for c in inspector.get_columns("pending_matches")]
        if "ean" not in columns_pending:
            logger.info("Adding 'ean' to pending_matches table...")
            try:
                conn.execute(text("ALTER TABLE pending_matches ADD COLUMN ean VARCHAR(50)"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add ean to pending_matches: {e}")

        # --- Table: price_alerts (Created by create_all, but check for created_at if old) ---
        # (Assuming it's new so skip for now)

    logger.info("Universal Migration finished successfully.")

if __name__ == "__main__":
    migrate()
