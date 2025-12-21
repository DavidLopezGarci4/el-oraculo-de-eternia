from src.infrastructure.database import SessionLocal
from src.domain.models import BlackcludedItemModel, PendingMatchModel

def recover_items():
    db = SessionLocal()
    targets = ["Beast", "Wind"] # Keywords for the missing items
    
    recovered_count = 0
    
    print(f"Searching for items containing: {targets}")
    
    for term in targets:
        # Find in Blacklist
        blacklisted = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.scraped_name.ilike(f"%{term}%")).all()
        
        for item in blacklisted:
            print(f"Recovering: {item.scraped_name} (ID: {item.id})")
            
            # Create Pending Entry
            pending = PendingMatchModel(
                scraped_name=item.scraped_name,
                price=0.0, # Price is lost in blacklist, default to 0 to force review
                currency="EUR",
                url=item.url,
                shop_name="ActionToys", # Assuming source
                image_url=None # Image might be lost, scraper re-run will fix or UI will show blank
            )
            
            db.add(pending)
            db.delete(item) # Remove from Blacklist
            recovered_count += 1
            
    db.commit()
    db.close()
    print(f"Operation Lazarus Complete: {recovered_count} items moved to Purgatory.")

if __name__ == "__main__":
    recover_items()
