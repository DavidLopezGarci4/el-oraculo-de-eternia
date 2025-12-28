import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

from src.infrastructure.database import engine

def run_rebrand_v2():
    print("Iniciando Rebrand Final: Unificacion tecnica (sin tildes)...")
    
    # Identidades a unificar hacia 'Fantasia Personajes'
    variants = ["Fantasia", "Fantasía Personajes", "Fantasia Personajes"]
    target = "Fantasia Personajes"
    
    tables = [
        ("offers", "shop_name"),
        ("pending_matches", "shop_name"),
        ("offer_history", "shop_name"),
        ("scraper_status", "spider_name"),
        ("scraper_execution_logs", "spider_name"),
        ("kaizen_insights", "spider_name")
    ]
    
    total_affected = 0
    
    with engine.connect() as conn:
        for table, column in tables:
            try:
                # Unify all variants to the target
                for variant in variants:
                    if variant == target: continue
                    
                    check = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {column} = :var"), {"var": variant})
                    count = check.scalar()
                    
                    if count > 0:
                        stmt = text(f"UPDATE {table} SET {column} = :target WHERE {column} = :var")
                        conn.execute(stmt, {"target": target, "var": variant})
                        print(f"Tabla '{table}': {count} filas migradas de '{variant}' -> '{target}'")
                        total_affected += count
                
                conn.commit()
            except Exception as e:
                print(f"Error en tabla '{table}': {e}")
    
    print(f"\nRebrand tecnico completado. Filas totales afectadas: {total_affected}")

if __name__ == "__main__":
    run_rebrand_v2()
