import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("backup_manager")

class BackupManager:
    """
    The Data Fortress of Eternia.
    Handles raw data snapshots, versioned DB backups, and emergency restoration.
    """
    def __init__(self, base_path: str = "backups"):
        self.base_path = Path(base_path)
        self.snapshots_path = self.base_path / "raw_snapshots"
        self.db_backups_path = self.base_path / "database"
        
        # Ensure directory structure
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
        self.db_backups_path.mkdir(parents=True, exist_ok=True)

    def save_raw_snapshot(self, shop_name: str, offers: List[Any]):
        """
        Saves the raw scraped data before any processing.
        Acts as the 'Flight Recorder' for scrapers.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_{shop_name}_{timestamp}.json"
        
        # Convert ScrapedOffer objects to dicts if needed
        serializable_offers = []
        for o in offers:
            if hasattr(o, '__dict__'):
                data = o.__dict__.copy()
                # Ensure complex objects like URLs are strings
                if 'url' in data: data['url'] = str(data['url'])
                serializable_offers.append(data)
            else:
                serializable_offers.append(o)

        file_path = self.snapshots_path / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(serializable_offers, f, ensure_ascii=False, indent=4)
            logger.info(f"🛡️ Raw snapshot saved: {filename} ({len(offers)} items)")
            
            # Retention: Keep only last 15 snapshots
            self._rotate_backups(self.snapshots_path, 15)
            
        except Exception as e:
            logger.error(f"❌ Failed to save raw snapshot: {e}")

    def create_database_backup(self, db_session):
        """
        Exports critical tables to a single JSON 'Vault' file.
        Tables: products, offers, pending_matches, offer_history.
        """
        from src.domain.models import ProductModel, OfferModel, PendingMatchModel, OfferHistoryModel
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eternia_vault_{timestamp}.json"
        
        vault = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.1-TOTAL"
            },
            "data": {
                "users": [],
                "products": [],
                "offers": [],
                "pending_matches": [],
                "offer_history": [],
                "price_alerts": [],
                "collection_items": [],
                "blackcluded_items": [],
                "kaizen_insights": [],
                "scraper_execution_logs": []
            }
        }

        try:
            # Helper to convert model to dict
            def to_dict(row):
                d = {}
                for column in row.__table__.columns:
                    val = getattr(row, column.name)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    d[column.name] = val
                return d

            from src.domain.models import (
                UserModel, ProductModel, OfferModel, PendingMatchModel, 
                OfferHistoryModel, PriceAlertModel, CollectionItemModel,
                BlackcludedItemModel, KaizenInsightModel, ScraperExecutionLogModel
            )

            # Extract data
            vault["data"]["users"] = [to_dict(u) for u in db_session.query(UserModel).all()]
            vault["data"]["products"] = [to_dict(p) for p in db_session.query(ProductModel).all()]
            vault["data"]["offers"] = [to_dict(o) for o in db_session.query(OfferModel).all()]
            vault["data"]["pending_matches"] = [to_dict(pm) for pm in db_session.query(PendingMatchModel).all()]
            vault["data"]["offer_history"] = [to_dict(h) for h in db_session.query(OfferHistoryModel).all()]
            vault["data"]["price_alerts"] = [to_dict(a) for a in db_session.query(PriceAlertModel).all()]
            vault["data"]["collection_items"] = [to_dict(ci) for ci in db_session.query(CollectionItemModel).all()]
            vault["data"]["blackcluded_items"] = [to_dict(bi) for bi in db_session.query(BlackcludedItemModel).all()]
            vault["data"]["kaizen_insights"] = [to_dict(ki) for ki in db_session.query(KaizenInsightModel).all()]
            vault["data"]["scraper_execution_logs"] = [to_dict(el) for el in db_session.query(ScraperExecutionLogModel).all()]

            file_path = self.db_backups_path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(vault, f, ensure_ascii=False, indent=2)
            
            logger.info(f"🏰 Database Vault created: {filename}")
            self._rotate_backups(self.db_backups_path, 7) # Keep 7 days of DB backups
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to create DB backup: {e}")
            return None

    def _rotate_backups(self, folder: Path, limit: int):
        """Removes oldest files if limit exceeded."""
        files = sorted(list(folder.glob("*.json")), key=os.path.getmtime)
        if len(files) > limit:
            for f in files[:-limit]:
                os.remove(f)
                logger.info(f"🗑️ Rotated old backup: {f.name}")
