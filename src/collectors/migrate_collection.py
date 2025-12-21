import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.product import ProductRepository
from src.domain.models import CollectionItemModel, ProductModel
from loguru import logger

def migrate_legacy_collection():
    """
    Lee 'data/MOTU/lista_MOTU.xlsx' y actualiza la tabla 'collection_items'
    marcando como adquiridos aquellos productos que tengan 'SÍ' en la columna 'Adquirido'.
    """
    excel_path = Path("data/MOTU/lista_MOTU_temp.xlsx")
    if not excel_path.exists():
        # Fallback to original if temp doesn't exist
        excel_path = Path("data/MOTU/lista_MOTU.xlsx")
        
    if not excel_path.exists():
        logger.error(f"Archivo no encontrado: {excel_path}")
        return

    logger.info(f"Iniciando migración de colección desde {excel_path}...")
    
    try:
        # Obtener todas las hojas
        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names
        logger.info(f"Hojas detectadas: {sheet_names}")
        
        db: Session = SessionLocal()
        repo = ProductRepository(db)
        
        total_migrated = 0
        total_not_found = 0
        
        for sheet in sheet_names:
            logger.info(f"Procesando hoja: {sheet}")
            # Leer cada hoja saltando la primera fila (título)
            df = pd.read_excel(excel_path, sheet_name=sheet, header=1)
            
            count_sheet = 0
            
            for index, row in df.iterrows():
                adquirido_val = str(row.get("Adquirido", "")).strip().lower()
                product_name = str(row.get("Name", "")).strip()
                
                # Detectar "Sí", "Si", "S", "s"
                if adquirido_val.startswith("s"):
                    product = repo.get_by_name(product_name)
                    
                    if product:
                        # Verificar si ya existe en la colección
                        existing_item = db.query(CollectionItemModel).filter_by(product_id=product.id).first()
                        
                        if not existing_item:
                            new_item = CollectionItemModel(
                                product_id=product.id,
                                acquired=True,
                                notes=f"Importado desde {sheet}"
                            )
                            db.add(new_item)
                            count_sheet += 1
                            logger.info(f"[{sheet}] Marcado como adquirido: {product_name}")
                    else:
                        # logger.warning(f"Producto en Excel pero NO en BD: {product_name}")
                        total_not_found += 1
            
            total_migrated += count_sheet
            db.commit() # Commit per sheet
        
        logger.success(f"Migración GLOBAL completada. {total_migrated} productos añadidos. {total_not_found} no encontrados en catálogo.")
        db.close()
        
    except Exception as e:
        logger.error(f"Error crítico en migración: {e}")

if __name__ == "__main__":
    migrate_legacy_collection()
