import pandas as pd
import shutil
import os
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
    owner = db.query(UserModel).order_by(UserModel.id).first()
    if not owner:
        logger.warning("No users found. Cannot assign ownership.")
        
    temp_path = EXCEL_PATH.with_name(EXCEL_PATH.name + ".tmp")
    
    try:
        logger.info(f"Reading Excel: {EXCEL_PATH}")
        # Avoid Permission Denied by creating a temporary copy
        shutil.copy2(EXCEL_PATH, temp_path)
        
        xls = pd.ExcelFile(temp_path)
        
        total_products = 0
        new_products = 0
        new_owned = 0
        
        # Mapping Sheet Names to Clean Lines
        LINE_MAP = {
            "Origins_Action_Figures_Checklis": "Origins",
            "Origins_Deluxe_Checklist": "Deluxe",
            "Origins_Exclusives_Checklist": "Exclusives",
            "Origins_Beasts_Vehicles_and_Pla": "Beasts/Vehicles",
            "Stranger_Things_Crossover_Check": "Stranger Things",
            "Turtles_of_Grayskull_Checklist": "TMNT",
            "Thundercats_Crossover_Checklist": "Thundercats",
            "Transformers_Collaboration_Chec": "Transformers",
            "Masters_of_the_WWE_Universe_Act": "WWE",
            "Masters_of_the_WWE_Universe_Rin": "WWE Rings"
        }
        
        for sheet_name in xls.sheet_names:
            logger.info(f"Processing Sheet: {sheet_name}")
            df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
            
            if "Name" not in df.columns:
                logger.warning(f"Skipping sheet {sheet_name}: 'Name' column not found.")
                continue
                
            p_line = LINE_MAP.get(sheet_name, "Origins")
            
            for _, row in df.iterrows():
                p_name_raw = row.get("Name")
                if pd.isna(p_name_raw): continue
                
                # Figure ID (ActionFigure411)
                p_fig_id = row.get("Figure ID")
                try:
                    p_fig_id = int(p_fig_id) if pd.notna(p_fig_id) else None
                except:
                    p_fig_id = None
                
                # Final Name with Line suffix
                p_name = f"{p_name_raw} ({p_line})"
                
                p_img = row.get("Image URL")
                if pd.isna(p_img): p_img = None
                
                p_owned = row.get("Adquirido")
                
                # 1. Product Sync
                product = None
                if p_fig_id:
                    product = db.query(repo.model).filter_by(figure_id=p_fig_id).first()
                if not product:
                    product = db.query(repo.model).filter_by(name=p_name).first()
                
                if not product:
                    product = repo.create({
                        "name": p_name,
                        "figure_id": p_fig_id,
                        "line": p_line,
                        "category": "Masters of the Universe",
                        "image_url": p_img
                    })
                    new_products += 1
                else:
                    should_commit = False
                    if p_img and not product.image_url:
                        product.image_url = p_img
                        should_commit = True
                    if p_fig_id and not product.figure_id:
                        product.figure_id = p_fig_id
                        should_commit = True
                    if p_line and not product.line:
                        product.line = p_line
                        should_commit = True
                    if should_commit:
                        db.commit()

                # 2. Ownership Sync
                if owner and p_owned == "Sí":
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
                
        logger.success(f"Sync Complete: {total_products} processed. {new_products} new products. {new_owned} new items.")
        
    except Exception as e:
        logger.error(f"Import Failed: {e}")
    finally:
        if temp_path.exists():
            os.remove(temp_path)
        db.close()

if __name__ == "__main__":
    import_excel_to_db()
