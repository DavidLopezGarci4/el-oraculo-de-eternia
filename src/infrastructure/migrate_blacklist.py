from sqlalchemy import create_engine
from src.core.config import settings
from src.domain.models import BlackcludedItemModel
from sqlalchemy import inspect

engine = create_engine(settings.DATABASE_URL)

def migrate():
    print("Checking tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "blackcluded_items" not in tables:
        print("Creating 'blackcluded_items' table...")
        BlackcludedItemModel.__table__.create(engine)
    else:
        print("'blackcluded_items' already exists.")

    print("Done.")

if __name__ == "__main__":
    migrate()
