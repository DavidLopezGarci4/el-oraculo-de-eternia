from src.infrastructure.database import SessionLocal
from src.domain.models import BlackcludedItemModel, PendingMatchModel, OfferModel

def recover_items():
    db = SessionLocal()
    
    # 1. Search in Blacklist for known lost boys
    targets = ["Cat", "Wind", "Guardian", "Beast"] 
    print(f"Searching Blacklist for: {targets}")
    
    recovered_count = 0
    for term in targets:
        items = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.scraped_name.ilike(f"%{term}%")).all()
        for item in items:
            print(f"RECOVERING from Blacklist: {item.scraped_name} (ID: {item.id})")
            pending = PendingMatchModel(
                scraped_name=item.scraped_name,
                price=0.0,
                currency="EUR",
                url=item.url,
                shop_name="ActionToys",
                image_url=None
            )
            db.add(pending)
            db.delete(item)
            recovered_count += 1
            
    # 2. Check Catalog (Offers) for Beast-Man
    print("\nChecking Catalog for 'Beast'...")
    offers = db.query(OfferModel).filter(OfferModel.url.ilike("%beast%")).all()
    for o in offers:
        print(f"FOUND in Catalog: {o.url}")
        
    db.commit()
    db.close()
    print(f"\nRecovery Complete: {recovered_count} items moved to Purgatory.")

if __name__ == "__main__":
    recover_items()
