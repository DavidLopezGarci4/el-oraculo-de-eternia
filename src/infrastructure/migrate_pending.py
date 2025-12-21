from src.infrastructure.database import engine, Base
from src.domain.models import PendingMatchModel
from sqlalchemy import inspect

def run_migration():
    inspector = inspect(engine)
    if "pending_matches" not in inspector.get_table_names():
        print("Creating 'pending_matches' table...")
        PendingMatchModel.__table__.create(engine)
        print("Done.")
    else:
        print("'pending_matches' table already exists.")

if __name__ == "__main__":
    run_migration()
