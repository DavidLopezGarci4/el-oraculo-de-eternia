from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings
from src.domain.base import Base

# FinOps: Hybrid Engine (SQLite for Dev, Postgres for Cloud)
# Fix deprecated 'postgres://' scheme from some providers (fly.io/render/supabase)
db_url = settings.DATABASE_URL
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    db_url, 
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

# Enable WAL Mode for SQLite Concurrency
if "sqlite" in settings.DATABASE_URL:
    try:
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    except Exception:
        pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database tables and runs migrations."""
    Base.metadata.create_all(bind=engine)
    try:
        from src.infrastructure.universal_migrator import migrate
        migrate()
    except Exception as e:
        print(f"Migration error: {e}")

def get_db():
    """Dependency for DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
