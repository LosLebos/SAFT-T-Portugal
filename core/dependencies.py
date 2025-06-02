from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

# Assuming correct import paths for sibling/parent modules
# e.g., from .. import models, database
# from ..core import security
# from ..crud import user_crud
# from ..schemas import user_schemas

import models # For models.User type hint
from database import get_session # To get DB session
from core import security # For decode_token_for_username and oauth2_scheme
from crud import user_crud # For get_user_by_username
from schemas import user_schemas # For TokenData (though not directly used in return here, good for context)

from fastapi import Request # For get_optional_current_user to access request state if needed
import logging # For logging issues in get_optional_current_user
from core.config import DEMO_USER_USERNAME # To fetch demo user

logger = logging.getLogger(__name__)


async def get_current_user(
    db: Session = Depends(get_session), 
    token: str = Depends(security.oauth2_scheme) # Requires token (auto_error=True by default)
) -> models.User:
    """
    Dependency to get the current user from a JWT token.
    Decodes the token, validates credentials, and fetches the user from the database.
    Raises HTTPException if token is invalid, user not found, or other auth errors.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        username = security.decode_token_for_username(token)
        # No need to check if username is None here, as decode_token_for_username would raise JWTError if 'sub' is missing.
    except JWTError as e: # Catches expired, invalid signature, missing 'sub', etc.
        logger.debug(f"JWTError while decoding token: {e}")
        raise credentials_exception
    
    user = user_crud.get_user_by_username(db, username=username)
    if user is None:
        # User in token not found in DB.
        logger.warning(f"User '{username}' from token not found in database.")
        raise credentials_exception # Treat as invalid credentials
    return user


async def get_optional_current_user(
    # request: Request, # request can be useful for logging or other context
    db: Session = Depends(get_session), 
    token: Optional[str] = Depends(security.oauth2_scheme_optional) # auto_error=False
) -> Optional[models.User]:
    """
    Dependency to optionally get the current user from a JWT token.
    If no token is provided, or if the token is invalid (e.g., expired, bad signature),
    it returns None without raising an HTTPException.
    Only if a user is decoded but not found in DB, it might log but still returns None.
    """
    if not token:
        logger.debug("No token provided for optional authentication.")
        return None
    
    try:
        username = security.decode_token_for_username(token)
    except JWTError as e:
        logger.warning(f"Invalid token provided for optional authentication: {e}. Proceeding as anonymous.")
        return None # Invalid token, treat as no user / anonymous
    
    user = user_crud.get_user_by_username(db, username=username)
    if user is None:
        logger.warning(f"User '{username}' from optional token not found in DB. Proceeding as anonymous.")
        return None # User from token not in DB, treat as no user
    
    logger.debug(f"Optional authentication successful for user: {user.username}")
    return user


async def get_current_user_or_demo_user(
    current_user_opt: Optional[models.User] = Depends(get_optional_current_user),
    db: Session = Depends(get_session)
) -> models.User:
    """
    Dependency that returns the currently authenticated active user if one exists,
    otherwise falls back to returning the pre-configured demo user.
    Raises HTTPException if the demo user cannot be found or is inactive.
    """
    if current_user_opt and current_user_opt.is_active:
        logger.debug(f"Authenticated active user found: {current_user_opt.username}")
        return current_user_opt
    
    logger.info("No active authenticated user from token, attempting to fall back to demo user.")
    demo_user = user_crud.get_user_by_username(db, username=DEMO_USER_USERNAME)
    
    if not demo_user or not demo_user.is_active:
        logger.error(f"Demo user '{DEMO_USER_USERNAME}' not found or is inactive. Demo mode unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Or 500
            detail="Demo environment not configured or demo user is inactive."
        )
    
    logger.info(f"Falling back to demo user: {demo_user.username}")
    return demo_user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user) # Uses the strict get_current_user
) -> models.User:
    """
    Dependency to get the current active user.
    Relies on get_current_user and then checks if the user is active.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Dependency to get the current active superuser.
    Relies on get_current_active_user and then checks if the user is a superuser.
    (Not strictly required by subtask but a common pattern)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="The user doesn't have enough privileges"
        )
    return current_user


if __name__ == '__main__':
    # These dependencies are for FastAPI and cannot be run directly as a script
    # without a running FastAPI application context and a way to provide a token.
    print("--- Core Dependencies (Illustrative) ---")
    print("This module provides FastAPI dependencies for authentication and authorization.")
    print("Key dependencies defined:")
    print("- get_current_user: Decodes JWT token and fetches user from DB.")
    print("- get_current_active_user: Ensures the fetched user is active.")
    print("- get_current_active_superuser: Ensures the user is active and a superuser.")
    print("\nTo test these, they need to be used within FastAPI endpoint definitions and called via HTTP requests.")
    print("--- End of Core Dependencies ---")
