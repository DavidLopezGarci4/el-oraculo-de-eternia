from sqlalchemy import create_engine
from src.core.config import settings
from src.infrastructure.repositories.base import Base
from src.domain.models import UserModel, ScraperStatusModel
from sqlalchemy import inspect

engine = create_engine(settings.DATABASE_URL)
from src.domain.models import UserModel, ScraperStatusModel
from sqlalchemy import inspect

def migrate():
    print("Checking tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "users" not in tables:
        print("Creating 'users' table...")
        UserModel.__table__.create(engine)
    else:
        print("'users' already exists.")

    if "scraper_status" not in tables:
        print("Creating 'scraper_status' table...")
        ScraperStatusModel.__table__.create(engine)
    else:
        print("'scraper_status' already exists.")

    print("Done.")

if __name__ == "__main__":
    migrate()
