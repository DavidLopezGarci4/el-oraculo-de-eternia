from src.infrastructure.database import SessionLocal
from src.domain.models import BlackcludedItemModel

db = SessionLocal()
items = db.query(BlackcludedItemModel).all()
print(f"Total Blacklisted: {len(items)}")
for i in items:
    print(f"ID: {i.id} | {i.scraped_name}")
db.close()
