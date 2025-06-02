from fastapi import Depends, HTTPException, status
from sqlmodel import Session
import logging

# Assuming correct import paths
import models # For models.User type hint
from database import get_session # To get DB session
from crud import user_crud # For get_user_by_username
from core.config import DEMO_USER_USERNAME # To fetch demo user

logger = logging.getLogger(__name__)

# All token-based authentication dependencies are removed.
# The application will now operate solely in a "demo user" context.

async def get_demo_user_context(db: Session = Depends(get_session)) -> models.User:
    """
    Dependency that always fetches and returns the pre-configured demo user.
    This is the primary user context provider after removing token authentication.
    Raises HTTPException if the demo user cannot be found or is inactive,
    as this indicates a critical misconfiguration for the application's
    current demo-only operational mode.
    """
    logger.debug(f"Attempting to fetch demo user for context: {DEMO_USER_USERNAME}")
    demo_user = user_crud.get_user_by_username(db, username=DEMO_USER_USERNAME)
    
    if not demo_user:
        logger.critical(f"CRITICAL FAILURE: Demo user '{DEMO_USER_USERNAME}' not found in the database. Application cannot operate.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Application demo environment is not configured correctly (demo user missing)."
        )
    
    if not demo_user.is_active:
        logger.critical(f"CRITICAL FAILURE: Demo user '{DEMO_USER_USERNAME}' is not active. Application cannot operate.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Application demo environment is not configured correctly (demo user inactive)."
        )
    
    logger.debug(f"Successfully fetched active demo user for context: {demo_user.username}")
    return demo_user


if __name__ == '__main__':
    print("--- Core Dependencies (Simplified for Demo-Only Mode) ---")
    print("This module now provides a dependency to fetch the demo user context.")
    print("Key dependency defined:")
    print("- get_demo_user_context: Fetches the demo user, raises critical error if unavailable or inactive.")
    print("\nThis dependency is intended for use in a FastAPI application where all operations run under a demo user context.")
    print("--- End of Core Dependencies ---")
