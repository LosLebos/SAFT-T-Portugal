from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from typing import Any

# Assuming correct import paths for sibling/parent modules
# e.g., from .. import models, database
# from ..core import security, dependencies
# from ..crud import user_crud
# from ..schemas import user_schemas

import models # For models.User type hint
from database import get_session # To get DB session
from core import security # For token creation, password verification
from core import dependencies # For get_current_active_user dependency
from crud import user_crud # For user creation and retrieval
from schemas import user_schemas # For Pydantic request/response models (UserCreate, UserRead, Token)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post("/register", response_model=user_schemas.UserRead)
async def register_new_user(
    *,
    db: Session = Depends(get_session),
    user_in: user_schemas.UserCreate
) -> models.User:
    """
    Create new user.
    """
    # Check if user already exists by username
    existing_user_by_username = user_crud.get_user_by_username(db, username=user_in.username)
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered.",
        )
    # Check if user already exists by email (if email is provided)
    if user_in.email:
        existing_user_by_email = user_crud.get_user_by_email(db, email=user_in.email)
        if existing_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered.",
            )
            
    created_user = user_crud.create_user(db=db, user_in=user_in)
    return created_user


@router.post("/token", response_model=user_schemas.Token)
async def login_for_access_token(
    db: Session = Depends(get_session), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Takes username and password from form data.
    """
    user = user_crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    access_token = security.create_access_token(
        data={"sub": user.username} # 'sub' is the standard claim for subject (username)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=user_schemas.UserRead)
async def read_users_me(
    current_user: models.User = Depends(dependencies.get_current_active_user)
) -> models.User:
    """
    Fetch the current logged-in user.
    """
    # The current_user is already validated and fetched by the dependency.
    # If it wasn't active, get_current_active_user would have raised an exception.
    return current_user


if __name__ == '__main__':
    # This router defines FastAPI endpoints. It's meant to be included in a FastAPI app (main.py).
    # Direct execution of this file doesn't run the server or make endpoints available.
    print("--- Auth Router (Illustrative) ---")
    print("This module defines authentication related API endpoints:")
    print("- POST /auth/register : Creates a new user.")
    print("- POST /auth/token    : Logs in a user and returns a JWT token.")
    print("- GET  /auth/users/me : Returns details of the currently authenticated user.")
    print("\nThese endpoints are designed to be used within a FastAPI application.")
    print("--- End of Auth Router ---")
