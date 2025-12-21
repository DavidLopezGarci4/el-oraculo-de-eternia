import sqlite3
from src.core.config import settings

def migrate_schema():
    print("Running schema migration for Price History...")
    conn = sqlite3.connect("oraculo.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE offers ADD COLUMN currency VARCHAR DEFAULT 'EUR'")
        print("Added 'currency' column.")
    except Exception as e:
        print(f"Skipped currency: {e}")

    try:
        cursor.execute("ALTER TABLE offers ADD COLUMN min_price FLOAT DEFAULT 0.0")
        print("Added 'min_price' column.")
    except Exception as e:
        print(f"Skipped min_price: {e}")

    try:
        cursor.execute("ALTER TABLE offers ADD COLUMN max_price FLOAT DEFAULT 0.0")
        print("Added 'max_price' column.")
    except Exception as e:
        print(f"Skipped max_price: {e}")
        
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate_schema()
