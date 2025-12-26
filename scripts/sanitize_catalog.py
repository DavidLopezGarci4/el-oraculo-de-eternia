from src.infrastructure.database import SessionLocal
from src.domain.models import ProductModel, OfferModel, CollectionItemModel
from loguru import logger

def sanitize_duplicates():
    """
    Finds transition duplicates:
    - Target: Product with figure_id AND name suffix (e.g., 'He-Man (Origins)')
    - Source: Product without figure_id OR name suffix (e.g., 'He-Man')
    """
    db = SessionLocal()
    try:
        import re
        
        def extract_411_id(url):
            if not url: return None
            # Match number before extension in actionfigure411 URLs
            match = re.search(r'-(\d+)\.(jpg|png|jpeg)', url)
            if match:
                return int(match.group(1))
            return None

        # 1. First, populate missing figure_ids using image URLs (Self-Correction)
        logger.info("Auto-patching missing figure_ids from image URLs...")
        all_products = db.query(ProductModel).all()
        for p in all_products:
            if p.figure_id is None and p.image_url:
                extracted_id = extract_411_id(p.image_url)
                if extracted_id:
                    p.figure_id = extracted_id
        db.commit()

        # 2. Get all products WITH figure_id (The 'True' products)
        # We process them to find dupes sharing same figure_id
        identified_products = db.query(ProductModel).filter(ProductModel.figure_id != None).all()
        
        # Dictionary to keep the 'best' version for each figure_id
        # Best = One with line suffix or most updated_at
        best_versions = {}
        for p in identified_products:
            fid = p.figure_id
            if fid not in best_versions:
                best_versions[fid] = p
            else:
                current_best = best_versions[fid]
                # Priority: Has '(Line)' > Newer
                has_line = "(" in p.name and ")" in p.name
                current_has_line = "(" in current_best.name and ")" in current_best.name
                
                if (has_line and not current_has_line) or (has_line == current_has_line and p.updated_at > current_best.updated_at):
                    best_versions[fid] = p

        merge_count = 0
        
        # 3. Final Merge Loop
        for fid, target in best_versions.items():
            # Find any other product with the same figure_id (duplicates)
            duplicates = db.query(ProductModel).filter(
                ProductModel.figure_id == fid,
                ProductModel.id != target.id
            ).all()

            # Also find by Raw Name if they still don't have an ID
            # Extract raw name
            raw_name = re.sub(r'\s*\([^)]*\)\s*$', '', target.name).strip()
            orphans = db.query(ProductModel).filter(
                ProductModel.name == raw_name,
                ProductModel.id != target.id,
                ProductModel.figure_id == None
            ).all()
            
            for dupe in list(duplicates) + list(orphans):
                logger.info(f"Merging '{dupe.name}' (ID {dupe.id}) -> '{target.name}' (ID {target.id}) [FID: {fid}]")
                
                # Move Offers
                for offer in dupe.offers:
                    offer.product_id = target.id
                
                # Move Collection
                c_items = db.query(CollectionItemModel).filter(CollectionItemModel.product_id == dupe.id).all()
                for ci in c_items:
                    exists = db.query(CollectionItemModel).filter(
                        CollectionItemModel.owner_id == ci.owner_id,
                        CollectionItemModel.product_id == target.id
                    ).first()
                    if not exists:
                        ci.product_id = target.id
                    else:
                        db.delete(ci)
                
                db.delete(dupe)
                merge_count += 1
        
        db.commit()
        logger.success(f"Full Sanitization Complete: {merge_count} duplicates/orphans merged.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Sanitization Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sanitize_duplicates()
