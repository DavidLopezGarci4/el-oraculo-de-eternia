import pandas as pd
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.product import ProductRepository
from src.domain.models import CollectionItemModel, UserModel

# Hardcoded for now, mimicking personal_collection.py defaults
EXCEL_PATH = Path("data/MOTU/lista_MOTU.xlsx")

def import_excel_to_db():
    """
    Reads the local Excel file (synced by external job) and updates:
    1. Product Catalog (new items)
    2. User Collection (items marked as 'Sí')
    """
    if not EXCEL_PATH.exists():
        logger.error(f"Excel file not found at {EXCEL_PATH}")
        return
        
    db: Session = SessionLocal()
    repo = ProductRepository(db)
    
    # Get Primary User (Admin) for ownership assignment
    # Assumption: The first user is the owner of the legacy Excel
    owner = db.query(UserModel).order_by(UserModel.id).first()
    if not owner:
        logger.warning("No users found. Cannot assign ownership.")
        
    try:
        logger.info(f"Reading Excel: {EXCEL_PATH}")
        xls = pd.ExcelFile(EXCEL_PATH)
        
        total_products = 0
        new_products = 0
        new_owned = 0
        
        for sheet_name in xls.sheet_names:
            logger.info(f"Processing Sheet: {sheet_name}")
            # Skip metadata sheets if any? assuming all are data
            
            # Read header from row 1 (0-index = 1) -> wait, personal_collection writes header at row 2 (index 1)?
            # personal_collection: startrow=1 (which is index 1, so row 2). Row 0 is title.
            # So headers are at index 1.
            df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
            
            # Normalize columns
            if "Name" not in df.columns:
                logger.warning(f"Skipping sheet {sheet_name}: 'Name' column not found.")
                continue
                
            # Disambiguation Config
            # Keys: Sheet keywords (lower case) -> Suffix
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
            
            # Names that are likely to be repeated across lines
            AMBIGUOUS_NAMES = {
                "He-Man", "Skeletor", "Man-At-Arms", "Teela", "Beast Man", 
                "Mer-Man", "Evil-Lyn", "Trap Jaw", "Tri-Klops", "Man-E-Faces",
                "Ram Man", "Stratos", "Hordak", "She-Ra", "King Hiss", "Zodac"
            }
            
            for _, row in df.iterrows():
                p_name = row.get("Name")
                if pd.isna(p_name): continue
                
                # --- Disambiguation Logic ---
                sheet_lower = sheet_name.lower()
                for key, suffix in CROSSOVER_MAP.items():
                    if key in sheet_lower:
                        # RIGOROUS DISAMBIGUATION:
                        # If items are in a Crossover sheet (e.g. "Turtles of Grayskull"),
                        # we MUST append the suffix to allow differentiation from standard Origins items.
                        # Example: "Clamp Champ" -> "Clamp Champ (TMNT)"
                        # This avoids merging with the regular "Clamp Champ".
                        p_name = f"{p_name} {suffix}"
                        break
                # ----------------------------
                if pd.isna(p_name): continue
                
                p_img = row.get("Image URL")
                p_img = p_img if pd.notna(p_img) else None
                
                p_owned = row.get("Adquirido") # "Sí" / "No"
                
                # 1. Product Sync
                product = repo.get_by_name(p_name)
                if not product:
                    product = repo.create({
                        "name": p_name,
                        "category": "Masters of the Universe",
                        "image_url": p_img
                    })
                    new_products += 1
                else:
                    # Update Image if missing
                    if p_img and not product.image_url:
                        product.image_url = p_img
                        db.commit()

                # 2. Ownership Sync (if User exists)
                if owner and p_owned == "Sí":
                    # Check if already in collection
                    exists_in_coll = db.query(CollectionItemModel).filter_by(
                        owner_id=owner.id, 
                        product_id=product.id
                    ).first()
                    
                    if not exists_in_coll:
                        ci = CollectionItemModel(owner_id=owner.id, product_id=product.id)
                        db.add(ci)
                        db.commit()
                        new_owned += 1
                        
                total_products += 1
                
        logger.success(f"Sync Complete: {total_products} processed. {new_products} new products. {new_owned} new items in Fortress.")
        
    except Exception as e:
        logger.error(f"Import Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_excel_to_db()
