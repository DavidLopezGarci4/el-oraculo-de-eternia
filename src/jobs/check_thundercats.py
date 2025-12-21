
from src.infrastructure.database import SessionLocal
from src.domain.models import ProductModel

db = SessionLocal()

terms = ["Thundercats", "Lion-O", "Cheetara", "Panthro", "Tygra", "Skell-Ra", "Battle Cat Man", "Panthor Man"]
print(f"--- Searching for {len(terms)} specific terms ---")
for term in terms:
    results = db.query(ProductModel).filter(ProductModel.name.ilike(f"%{term}%")).all()
    if results:
        print(f"FOUND '{term}':")
        for r in results:
            print(f"  - ID: {r.id} | Name: {r.name} | Category: {r.category}")
    else:
        print(f"MISSING '{term}'")

print("\n--- Checking all 'He-Man' entries ---")
he_mans = db.query(ProductModel).filter(ProductModel.name == "He-Man").all()
for hm in he_mans:
    print(f"  - ID: {hm.id} | Name: {hm.name} | Category: {hm.category} | Image: {hm.image_url}")

print("\n--- Checking 'He-Man' with similar names ---")
he_mans_like = db.query(ProductModel).filter(ProductModel.name.ilike("%He-Man%")).all()
for hm in he_mans_like:
    if hm.name != "He-Man":
         print(f"  - ID: {hm.id} | Name: {hm.name} | Category: {hm.category}")
