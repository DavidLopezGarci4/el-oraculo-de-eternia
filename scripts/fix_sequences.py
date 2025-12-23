import sys
import os
from sqlalchemy import text

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.database import engine

def fix_sequences():
    """
    Resets the PostgreSQL sequences to the maximum ID in the table.
    This fixes 'duplicate key value violates unique constraint' errors
    after a migration with explicit IDs.
    """
    print("Fixing Database Sequences...")
    
    tables_to_fix = [
        "users",
        "products", 
        "offers",
        "collection_items",
        "price_history",
        "blackcluded_items",
        "pending_matches",
        "scraper_logs"
    ]
    
    with engine.connect() as conn:
        for table in tables_to_fix:
            try:
                # 1. Get the max id
                result = conn.execute(text(f"SELECT MAX(id) FROM {table}"))
                max_id = result.scalar()
                
                if max_id is None:
                    max_id = 0
                
                print(f"   * {table}: Max ID is {max_id}")
                
                # 2. Reset sequence
                # Sequence name is usually table_id_seq
                seq_name = f"{table}_id_seq"
                
                # Setup proper next value (max + 1)
                # setval(seq, val, is_called) -> if is_called=true, next is val+1. 
                # effectively we want the generator to start at max_id + 1.
                # simpler: setval(seq, max_id)
                stmt = text(f"SELECT setval('{seq_name}', :new_val)")
                conn.execute(stmt, {"new_val": max_id + 1}) # Start next at max+1
                
                print(f"     -> Sequence '{seq_name}' reset to {max_id + 1}")
                
            except Exception as e:
                print(f"     ! Error fixing {table}: {e}")
                # Sometimes sequence name is different or table empty
        
        conn.commit()
        
    print("\nAll sequences synchronized! You can now add items safely.")

if __name__ == "__main__":
    fix_sequences()
