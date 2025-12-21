from sqlalchemy import text
from src.infrastructure.database import SessionLocal, engine
from src.domain.models import Base

def recreate_table():
    with engine.connect() as conn:
        print("Recreating collection_items table to fix constraints...")
        
        # 1. Rename old table
        try:
            conn.execute(text("ALTER TABLE collection_items RENAME TO collection_items_old"))
        except Exception as e:
            print(f"Rename failed (maybe already renamed?): {e}")

        # 2. Create new table (SQL Definition based on new Model)
        # Note: product_id is NOT UNIQUE here.
        create_sql = """
        CREATE TABLE collection_items (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            acquired BOOLEAN DEFAULT 0,
            condition VARCHAR DEFAULT 'New',
            notes VARCHAR,
            acquired_at DATETIME,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );
        """
        conn.execute(text(create_sql))
        
        # 3. Copy Data
        # We assume owner_id was populated by previous script (default 1)
        # If previous script added column but failed on constraint, owner_id exists in old table.
        try:
            conn.execute(text("""
                INSERT INTO collection_items (id, product_id, owner_id, acquired, condition, notes, acquired_at)
                SELECT id, product_id, owner_id, acquired, condition, notes, acquired_at FROM collection_items_old
            """))
            print("Data copied successfully.")
        except Exception as e:
            print(f"Copy failed: {e}")
            
        # 4. Drop old
        conn.execute(text("DROP TABLE collection_items_old"))
        
        # 5. Create Indices manually or let SQLAlchemy do it? 
        # We need index on product_id and owner_id for performance
        conn.execute(text("CREATE INDEX ix_collection_items_product_id ON collection_items (product_id)"))
        conn.execute(text("CREATE INDEX ix_collection_items_owner_id ON collection_items (owner_id)"))
        
        conn.commit()
    print("Recreation process complete.")

if __name__ == "__main__":
    recreate_table()
