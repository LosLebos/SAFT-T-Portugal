from typing import Optional
from sqlmodel import Session, select

# Assuming models.py is accessible
# Adjust paths if using a different project structure.
# e.g., from .. import models
import models # This should give access to models.User (the SQLModel class)
# user_schemas is being removed, so UserCreate will not be used here.
from core.security import get_password_hash # For hashing password before saving

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Fetches a user by their username from the database.
    """
    statement = select(models.User).where(models.User.username == username)
    user = db.exec(statement).first()
    return user

# get_user_by_email is being removed as per instructions.

def create_user(
    db: Session, 
    username: str, 
    hashed_password: str, # Expecting already hashed password for demo user, or raw if called elsewhere
    email: Optional[str] = None,
    is_active: bool = True,
    is_superuser: bool = False
) -> models.User:
    """
    Creates a new user in the database.
    Accepts direct parameters instead of a UserCreate schema.
    The password should be pre-hashed if this function is only for demo user creation with a known hash.
    Or, if it's for general use, it should take plain password and hash it.
    Given demo_data.py calls this with a plain password and core.security.get_password_hash,
    this function should expect a PLAIN password and hash it, or demo_data.py should pre-hash.
    Let's adjust: create_user will still hash the password.
    The previous `create_user` in `demo_data.py` used `UserCreate` which had a plain password.
    So, this `create_user` should also take a plain password and hash it.
    """
    
    # Re-confirming: get_password_hash is still in core.security
    # So this function should take plain_password and hash it.
    # The call from demo_data.py:
    # user_in = user_schemas.UserCreate(username=DEMO_USER_USERNAME, password=DEMO_USER_PASSWORD, email=...)
    # demo_user = user_crud.create_user(db, user_in) 
    # This implies create_user was expecting UserCreate which has plain password.
    # So, the new signature should be: username, plain_password, email.

# Corrected signature based on how demo_data will call it (implicitly, after UserCreate is removed from there)
# demo_data.py will need to be updated to call this with new signature.
# For now, let's assume demo_data.py will be modified to pass parameters directly.

# Simpler: create_user for demo data will be called from demo_data.py which will handle hashing.
# This function will now expect a hashed_password.
# No, let's keep hashing responsibility here for consistency if it were ever used elsewhere.
# The caller (demo_data.py) will provide plain password.

def create_user( # Renaming plain_password to password for clarity as it's an input.
    db: Session, 
    username: str, 
    password: str, # Plain password
    email: Optional[str] = None,
    is_active: bool = True,
    is_superuser: bool = False
) -> models.User:
    """
    Creates a new user in the database. Hashes the plain password.
    """
    hashed_password_val = get_password_hash(password)
    
    db_user = models.User(
        username=username,
        email=email, 
        hashed_password=hashed_password_val,
        is_active=is_active,
        is_superuser=is_superuser
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
