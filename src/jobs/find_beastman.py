import sys
import os
from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

from src.infrastructure.database import SessionLocal
from src.domain.models import ProductModel, PendingMatchModel
from sqlalchemy import or_

def check_beast_man():
    db = SessionLocal()
    try:
        print("--- SEARCHING PRODUCTS (CATALOG) ---")
        products = db.query(ProductModel).filter(
            or_(
                ProductModel.name.ilike("%beast%"),
                ProductModel.name.ilike("%tmnt%"),
                ProductModel.name.ilike("%turtles%")
            )
        ).all()
        
        if not products:
            print("No matches in Catalog.")
        for p in products:
            print(f" [CATALOG] ID: {p.id} | Name: {p.name}")

        print("\n--- SEARCHING PURGATORY (PENDING) ---")
        pending = db.query(PendingMatchModel).filter(
            or_(
                PendingMatchModel.scraped_name.ilike("%beast%"),
                PendingMatchModel.scraped_name.ilike("%tmnt%"),
                PendingMatchModel.scraped_name.ilike("%turtles%")
            )
        ).all()

        if not pending:
            print("No matches in Purgatory.")
        for p in pending:
            print(f" [PENDING] ID: {p.id} | Scraped: {p.scraped_name} | URL: {p.url}")

    finally:
        db.close()

if __name__ == "__main__":
    check_beast_man()
