import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

from src.infrastructure.database import engine

def run_rebrand():
    # Force UTF-8 if possible or use safe strings
    print("Iniciando Rebrand: Fantasia -> Fantasia Personajes...")
    
    updates = [
        ("offers", "shop_name"),
        ("pending_matches", "shop_name"),
        ("offer_history", "shop_name"),
        ("scraper_status", "spider_name"),
        ("scraper_execution_logs", "spider_name"),
        ("kaizen_insights", "spider_name")
    ]
    
    total_affected = 0
    
    with engine.connect() as conn:
        for table, column in updates:
            try:
                # Check if table exists
                check = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {column} = 'Fantasia'"))
                count = check.scalar()
                
                if count > 0:
                    # Note: Using 'Fantasía Personajes' with accent. SQLAlchemy handles this via parameters usually.
                    # But the print should be safe.
                    stmt = text(f"UPDATE {table} SET {column} = :new_name WHERE {column} = 'Fantasia'")
                    conn.execute(stmt, {"new_name": "Fantasía Personajes"})
                    conn.commit()
                    print(f"Tabla '{table}': {count} filas actualizadas.")
                    total_affected += count
                else:
                    print(f"Tabla '{table}': Sin registros de 'Fantasia'.")
            except Exception as e:
                print(f"Error en tabla '{table}': {e}")
    
    print(f"\nRebrand completado. Filas totales afectadas: {total_affected}")

if __name__ == "__main__":
    run_rebrand()
