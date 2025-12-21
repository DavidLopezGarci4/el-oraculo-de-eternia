from src.infrastructure.database import SessionLocal
from src.domain.models import PendingMatchModel, OfferModel, ScraperStatusModel, ProductModel

db = SessionLocal()

print("--- DIAGNOSTICS ---")
pending_count = db.query(PendingMatchModel).count()
offer_count = db.query(OfferModel).count()
product_count = db.query(ProductModel).count()
status_rows = db.query(ScraperStatusModel).all()

print(f"Pending Matches (Purgatory): {pending_count}")
print(f"Active Offers (Catalog): {offer_count}")
print(f"Products (Catalog Definitions): {product_count}")
print("\nScraper Status:")
for s in status_rows:
    print(f"- {s.spider_name}: {s.status} (Items: {s.items_scraped}) Last Update: {s.last_update}")

db.close()
