from src.infrastructure.database import engine
from src.domain.models import Base, PriceHistoryModel

def run_migration():
    print("Creating tables...")
    # This will create the table if it doesn't exist.
    # It won't affect existing tables unless we drop them (which we won't).
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    run_migration()
