from sqlalchemy import text
from src.infrastructure.database import SessionLocal, engine

def migrate_ownership():
    """
    Adds owner_id column to collection_items and drops unique constraint on product_id.
    """
    with engine.connect() as conn:
        print("Migrating collection_items table...")
        
        # 1. Add owner_id column (nullable first to avoid constraint fail on existing rows)
        try:
            conn.execute(text("ALTER TABLE collection_items ADD COLUMN owner_id INTEGER REFERENCES users(id)"))
            print("Added owner_id column.")
        except Exception as e:
            print(f"Column owner_id might already exist: {e}")
            
        # 2. Update existing rows to default owner (User ID 1)
        try:
            conn.execute(text("UPDATE collection_items SET owner_id = 1 WHERE owner_id IS NULL"))
            print("Updated existing items to owner_id=1")
        except Exception as e:
            print(f"Update failed: {e}")
            
        # SQLite doesn't support DROP CONSTRAINT easily.
        # We need to recreate the table or just iterate.
        # However, `unique=True` on product_id in SQLite is an index.
        # We can try dropping the index if we know its name. 
        # Usually `sqlite_autoindex_collection_items_1`.
        
        try:
            # Check indices
            result = conn.execute(text("PRAGMA index_list(collection_items)"))
            for row in result:
                idx_name = row[1]
                is_unique = row[2]
                if is_unique:
                    print(f"Dropping unique index: {idx_name}")
                    conn.execute(text(f"DROP INDEX {idx_name}"))
        except Exception as e:
            print(f"Index drop failed (might be constraint): {e}")
            
        conn.commit()
    print("Migration attempt complete.")

if __name__ == "__main__":
    migrate_ownership()
