
import os
import sys
from pathlib import Path

# Add src to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.core.config import settings
from src.domain.models import (
    Base, ProductModel, ScraperExecutionLogModel, UserModel, ScraperStatusModel,
    OfferModel, CollectionItemModel, PendingMatchModel, BlackcludedItemModel, PriceHistoryModel
)

def migrate_data(target_db_url):
    """
    Migrates data from local SQLite to Target PostgreSQL.
    """
    if not target_db_url:
        print("❌ Error: DATABASE_URL not provided.")
        return

    print(f"🚀 Starting Migration to: {target_db_url.split('@')[1] if '@' in target_db_url else 'Target DB'}")

    # 1. Source DB (SQLite)
    sqlite_url = "sqlite:///./oraculo.db"
    source_engine = create_engine(sqlite_url)
    SourceSession = sessionmaker(bind=source_engine)
    source_session = SourceSession()

    # 2. Target DB (Postgres)
    if target_db_url.startswith("postgres://"):
        target_db_url = target_db_url.replace("postgres://", "postgresql://", 1)
        
    target_engine = create_engine(target_db_url)
    TargetSession = sessionmaker(bind=target_engine)
    
    # Create Tables in Target
    print("🛠️ Creating tables in target database...")
    Base.metadata.create_all(target_engine)
    
    target_session = TargetSession()
    
    try:
        # Order matters for Foreign Keys!
        
        # 1. Users
        print("📦 Migrating Users...")
        users = source_session.query(UserModel).all()
        for u in users:
            target_session.merge(u)
        target_session.flush()

        # 2. Products
        print("📦 Migrating Products...")
        products = source_session.query(ProductModel).all()
        for p in products:
            target_session.merge(p)
        target_session.flush()

        # 3. Offers (Depend on Products)
        print("📦 Migrating Offers...")
        offers = source_session.query(OfferModel).all()
        for o in offers:
            target_session.merge(o)
        target_session.flush()

        # 4. Price History (Depends on Offers)
        print("📦 Migrating Price History...")
        history = source_session.query(PriceHistoryModel).all()
        for h in history:
            target_session.merge(h)
        
        # 5. Collection (Tablero) (Depends on User + Product)
        print("📦 Migrating Collection (Tablero)...")
        collection = source_session.query(CollectionItemModel).all()
        for c in collection:
            target_session.merge(c)
            
        # 6. Purgatory (Pending Matches)
        print("📦 Migrating Purgatory (Pending)...")
        pending = source_session.query(PendingMatchModel).all()
        for item in pending:
            target_session.merge(item)

        # 7. Blacklist
        print("📦 Migrating Blacklist...")
        black = source_session.query(BlackcludedItemModel).all()
        for b in black:
            target_session.merge(b)

        # 8. Logs & Status
        print("📦 Migrating Logs & Status...")
        logs = source_session.query(ScraperExecutionLogModel).all()
        for l in logs:
            target_session.merge(l)
            
        status = source_session.query(ScraperStatusModel).all()
        for s in status:
            target_session.merge(s)
            
        target_session.commit()
        print("✅ Migration Complete! Data is now in the cloud. ☁️")
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        target_session.rollback()
    finally:
        source_session.close()
        target_session.close()

if __name__ == "__main__":
    import argparse
    from src.core.config import settings
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Target Database URL (Postgres)", required=False)
    args = parser.parse_args()
    
    target_url = args.url or settings.DATABASE_URL
    
    if "sqlite" in target_url:
        print("⚠️  Warning: DATABASE_URL in .env is pointing to SQLite.")
        print("Please provide the Supabase URL explicitly: python scripts/migrate_to_cloud.py --url \"postgres://...\"")
    else:
        migrate_data(target_url)
