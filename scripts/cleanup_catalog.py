import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.database import SessionLocal
from src.domain.models import ProductModel, OfferModel, CollectionItemModel, PendingMatchModel

EXCEL_PATH = Path("data/MOTU/lista_MOTU.xlsx")

def cleanup():
    if not EXCEL_PATH.exists():
        print(f"Error: {EXCEL_PATH} not found.")
        return

    print(f"Reading master list from {EXCEL_PATH}...")
    xls = pd.ExcelFile(EXCEL_PATH)
    
    CROSSOVER_MAP = {
        "thundercats": "(Thundercats)",
        "turtles": "(TMNT)",
        "tmnt": "(TMNT)",
        "street fighter": "(Street Fighter)",
        "stranger": "(Stranger Things)",
        "wwe": "(WWE)",
        "collaboration": "(Collab)",
        "transformers": "(Transformers)"
    }

    master_names = set()
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
        if "Name" not in df.columns:
            continue
            
        for _, row in df.iterrows():
            name = row.get("Name")
            if pd.isna(name): continue
            
            # Disambiguation
            sheet_lower = sheet_name.lower()
            for key, suffix in CROSSOVER_MAP.items():
                if key in sheet_lower:
                    name = f"{name} {suffix}"
                    break
            
            master_names.add(str(name).strip())

    print(f"Master list loaded: {len(master_names)} unique names.")

    db: Session = SessionLocal()
    try:
        all_db_products = db.query(ProductModel).all()
        to_delete = []
        
        for p in all_db_products:
            if p.name not in master_names:
                to_delete.append(p)

        print(f"Found {len(to_delete)} products not in master list.")
        
        for p in to_delete:
            print(f"Deleting rogue product: {p.name}")
            # Offers are cascade deleted by relationship config in models.py
            db.delete(p)
            
        db.commit()
        print(f"Successfully deleted {len(to_delete)} products.")
        
        final_count = db.query(ProductModel).count()
        print(f"Final Product Count in DB: {final_count}")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
