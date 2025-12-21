from src.infrastructure.database import SessionLocal
from src.domain.models import UserModel
from src.core.security import hash_password

def restore_david():
    db = SessionLocal()
    try:
        # Check if ID 1 exists (it shouldn't based on audit)
        u = db.query(UserModel).filter(UserModel.id == 1).first()
        if u:
            print(f"User ID 1 already exists: {u.username}")
            return

        print("Restoring User 'David' with ID=1...")
        # Force ID 1 to match existing collection_items
        david = UserModel(
            id=1,
            username="David",
            email="david@example.com", # Placeholder
            hashed_password=hash_password("admin"), # Temp password
            role="admin",
            is_active=True
        )
        db.add(david)
        db.commit()
        print("David restored! Password set to 'admin'. Please change it immediately.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    restore_david()
