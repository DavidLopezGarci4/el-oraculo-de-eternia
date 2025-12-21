from src.infrastructure.database import SessionLocal
from src.domain.models import PendingMatchModel, OfferModel, BlackcludedItemModel, ProductModel

db = SessionLocal()
pending = db.query(PendingMatchModel).count()
offers = db.query(OfferModel).count()
blacklist = db.query(BlackcludedItemModel).count()
products = db.query(ProductModel).count()

print(f"PENDING (Purgatory): {pending}")
print(f"OFFERS (Matched): {offers}")
print(f"BLACKLIST (Ignored): {blacklist}")
print(f"PRODUCTS (Catalog): {products}")

# Sample blacklist items to see if they are valid or accidental mass delete
if blacklist > 0:
    print("\nSample Blacklisted Items:")
    for item in db.query(BlackcludedItemModel).order_by(BlackcludedItemModel.id.desc()).limit(5):
        print(f"- {item.scraped_name} ({item.url})")

db.close()
