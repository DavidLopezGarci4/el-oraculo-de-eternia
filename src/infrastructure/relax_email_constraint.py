import sqlite3
# from src.infrastructure.database import DATABASE_URL

def relax_email_constraint():
    # Parse DB path from URL (sqlite:///./oraculo.db)
    db_path = "oraculo.db" # Correct DB Name
    
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Disable Foreign Keys
        cursor.execute("PRAGMA foreign_keys = OFF;")

        # Pre-cleanup: Drop users_old if it exists from failed runs
        cursor.execute("DROP TABLE IF EXISTS users_old;")
        
        # 2. Rename existing table
        print("Renaming users table...")
        cursor.execute("ALTER TABLE users RENAME TO users_old;")
        
        # 3. Create NEW table (without UNIQUE on email)
        # We manually define the schema to ensure it matches desired state
        print("Creating new users table...")
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER NOT NULL PRIMARY KEY, 
                username VARCHAR NOT NULL, 
                email VARCHAR NOT NULL, 
                hashed_password VARCHAR NOT NULL, 
                role VARCHAR, 
                is_active BOOLEAN,
                created_at DATETIME
            );
        """)
        
        # Re-create index on username
        # Drop old indices first (they might still exist pointing to users_old or just name conflict)
        cursor.execute("DROP INDEX IF EXISTS ix_users_username;")
        cursor.execute("DROP INDEX IF EXISTS ix_users_id;")
        
        cursor.execute("CREATE UNIQUE INDEX ix_users_username ON users (username);")
        cursor.execute("CREATE INDEX ix_users_id ON users (id);")
        
        # 4. Copy Data
        print("Copying data...")
        # Note: Columns must match order or be explicit.
        # Check columns in old table?
        # Standard columns: id, username, email, hashed_password, role, is_active, created_at
        cursor.execute("""
            INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at)
            SELECT id, username, email, hashed_password, role, is_active, created_at
            FROM users_old;
        """)
        
        # 5. Drop Old Table
        print("Dropping old table...")
        cursor.execute("DROP TABLE users_old;")
        
        # 6. Re-enable keys (Check integrity)
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.commit()
        print("Migration successful: Email unique constraint removed.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    relax_email_constraint()
