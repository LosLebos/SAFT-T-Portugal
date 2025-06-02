from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$") # Basic username validation
    email: Optional[EmailStr] = None # Using Pydantic's EmailStr for validation

class UserCreate(UserBase):
    password: str = Field(..., min_length=8) # Ensure password has a minimum length

class UserRead(UserBase):
    id: int
    is_active: bool = True
    is_superuser: bool = False

    class Config:
        # Pydantic V1 used `orm_mode = True`
        # Pydantic V2 uses `from_attributes = True`
        from_attributes = True 
        # This allows the model to be created from ORM objects (like SQLModel instances)
        # e.g., UserRead.from_orm(db_user_object) or UserRead.model_validate(db_user_object) in Pydantic V2

# Schema for updating a user (example, not strictly required by current subtask but good practice)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


if __name__ == '__main__':
    # Example Usage
    print("--- User Schema Examples ---")

    # UserCreate Example
    try:
        user_create_data = {"username": "newuser", "email": "newuser@example.com", "password": "VeryStrongPassword123"}
        user_c = UserCreate(**user_create_data)
        print(f"UserCreate valid: {user_c.model_dump_json(indent=2)}")
        
        user_create_invalid_username = {"username": "nu", "email": "newuser@example.com", "password": "password123"}
        UserCreate(**user_create_invalid_username) # Should fail username length
    except Exception as e:
        print(f"Error in UserCreate (expected for invalid): {e}")

    try:
        user_create_invalid_password = {"username": "newuser2", "email": "newuser2@example.com", "password": "short"}
        UserCreate(**user_create_invalid_password) # Should fail password length
    except Exception as e:
        print(f"Error in UserCreate (expected for invalid password): {e}")
        
    # UserRead Example (simulating creation from a DB object like structure)
    # In a real scenario, you'd use UserRead.model_validate(db_user_sqlmodel_instance)
    db_user_data = {
        "id": 1,
        "username": "dbuser",
        "email": "dbuser@example.com",
        "hashed_password": "somehash", # Not included in UserRead
        "is_active": True,
        "is_superuser": False
    }
    # Simulate SQLModel object by creating a simple class or dict
    class DBUserSim:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    db_user_sim_instance = DBUserSim(**db_user_data)
    
    try:
        user_r = UserRead.model_validate(db_user_sim_instance) # Pydantic V2
        # user_r = UserRead.from_orm(db_user_sim_instance) # Pydantic V1
        print(f"\nUserRead valid: {user_r.model_dump_json(indent=2)}")
    except Exception as e:
        print(f"Error in UserRead: {e}")

    # Token Example
    token_data = {"access_token": "sampleaccesstokenstring", "token_type": "bearer"}
    token_m = Token(**token_data)
    print(f"\nToken model valid: {token_m.model_dump_json(indent=2)}")

    print("\n--- End of User Schema Examples ---")
