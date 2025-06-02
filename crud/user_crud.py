from typing import Optional
from sqlmodel import Session, select

# Assuming models.py and schemas/user_schemas.py are accessible
# Adjust paths if using a different project structure.
# e.g., from .. import models
# from ..schemas import user_schemas
import models # This should give access to models.User (the SQLModel class)
from schemas import user_schemas # This gives access to user_schemas.UserCreate etc.
from core.security import get_password_hash # For hashing password before saving

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Fetches a user by their username from the database.
    """
    statement = select(models.User).where(models.User.username == username)
    user = db.exec(statement).first()
    return user

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    Fetches a user by their email from the database.
    """
    if not email: # Guard against querying with None or empty email if it's optional but unique
        return None
    statement = select(models.User).where(models.User.email == email)
    user = db.exec(statement).first()
    return user

def create_user(db: Session, user_in: user_schemas.UserCreate) -> models.User:
    """
    Creates a new user in the database.
    """
    hashed_password = get_password_hash(user_in.password)
    
    # Create the SQLModel User instance
    db_user = models.User(
        username=user_in.username,
        email=user_in.email, # Will be None if not provided in UserCreate
        hashed_password=hashed_password,
        is_active=True, # Default new users to active, can be changed by admin
        is_superuser=False # Default new users to not superuser
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user) # To get the ID and any other DB-generated fields
    return db_user


if __name__ == '__main__':
    # Example usage - Requires a database session and engine setup.
    # This is more for illustration; actual testing should be done via test suite.
    print("--- User CRUD Examples (Illustrative - Requires DB Setup) ---")

    # To run this, you'd need to set up an engine and session similar to database.py
    # from sqlmodel import create_engine
    # from database import DATABASE_URL # Assuming a test DB URL or a disposable one
    #
    # if "sqlite" not in DATABASE_URL: # Avoid running on non-test DB by mistake
    #     print("Skipping illustrative CRUD example as DATABASE_URL is not SQLite.")
    # else:
    #     engine = create_engine(DATABASE_URL, echo=True)
    #     SQLModel.metadata.create_all(engine) # Ensure User table is created
    #
    #     with Session(engine) as session:
    #         print("\n1. Attempting to create a new user...")
    #         new_user_data = user_schemas.UserCreate(
    #             username="crud_testuser",
    #             email="crud_test@example.com",
    #             password="aSecurePassword123"
    #         )
    #         try:
    #             # Check if user already exists before creating
    #             existing_user = get_user_by_username(session, new_user_data.username)
    #             if existing_user:
    #                 print(f"User '{new_user_data.username}' already exists. Skipping creation.")
    #                 created_db_user = existing_user
    #             else:
    #                 created_db_user = create_user(session, new_user_data)
    #                 print(f"User created: ID={created_db_user.id}, Username='{created_db_user.username}'")
    #
    #             print("\n2. Attempting to fetch the created user by username...")
    #             fetched_user = get_user_by_username(session, created_db_user.username)
    #             if fetched_user:
    #                 print(f"Fetched user: ID={fetched_user.id}, Username='{fetched_user.username}', Email='{fetched_user.email}'")
    #             else:
    #                 print(f"User '{created_db_user.username}' not found after creation (unexpected).")
    #
    #             print("\n3. Attempting to fetch user by email...")
    #             if created_db_user.email:
    #                 fetched_by_email = get_user_by_email(session, created_db_user.email)
    #                 if fetched_by_email:
    #                     print(f"Fetched by email: ID={fetched_by_email.id}, Username='{fetched_by_email.username}'")
    #                 else:
    #                     print(f"User with email '{created_db_user.email}' not found.")
    #
    #             print("\n4. Attempting to fetch a non-existent user...")
    #             non_existent_user = get_user_by_username(session, "nosuchuser")
    #             if non_existent_user is None:
    #                 print("Correctly determined that 'nosuchuser' does not exist.")
    #             else:
    #                 print("Error: 'nosuchuser' was found (unexpected).")
    #
    #         except Exception as e:
    #             print(f"An error occurred during CRUD example: {e}")
    #         finally:
    #             # Clean up: delete the created user if it exists and was created by this test run.
    #             # This is tricky without knowing if it pre-existed. Test suites handle this better.
    #             # For this example, manual cleanup might be needed if run multiple times on same DB.
    #             # For instance:
    #             # user_to_delete = get_user_by_username(session, "crud_testuser")
    #             # if user_to_delete:
    #             #     session.delete(user_to_delete)
    #             #     session.commit()
    #             #     print(f"Cleaned up user 'crud_testuser'.")
    #             pass
    
    print("\nNote: The above example is illustrative. Run tests for actual CRUD validation.")
    print("--- End of User CRUD Examples ---")
