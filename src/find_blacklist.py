from src.infrastructure.database import SessionLocal
from src.domain.models import BlackcludedItemModel

db = SessionLocal()
terms = ["Beast", "Wind"]
print(f"Searching Blacklist for terms: {terms}")

found = []
for term in terms:
    items = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.scraped_name.ilike(f"%{term}%")).all()
    for i in items:
        print(f"FOUND: ID={i.id} | Name={i.scraped_name} | URL={i.url}")
        found.append(i.id)

print(f"Total Found: {len(found)}")
db.close()
