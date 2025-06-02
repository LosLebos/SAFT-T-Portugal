from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

# --- Configuration ---
# In a real app, load from environment variables or a config file.
SECRET_KEY = "your-super-secret-key-for-development-CHANGE-ME" # IMPORTANT: Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Password Hashing ---
# Use bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # tokenUrl points to the login endpoint
# Optional OAuth2 scheme for endpoints that can be accessed by authenticated or anonymous (demo) users
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


# --- Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token.

    Args:
        data: Dictionary to be encoded in the token (typically contains 'sub' for username).
        expires_delta: Optional timedelta for token expiry. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        The encoded JWT token as a string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    # Ensure 'sub' (subject/username) is present, as it's standard
    if "sub" not in to_encode:
        raise ValueError("Missing 'sub' (subject/username) in token data.")
        
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token_for_username(token: str) -> Optional[str]:
    """
    Decodes a JWT token and extracts the username (subject).

    Args:
        token: The JWT token string.

    Returns:
        The username (str) if token is valid and username is present, None otherwise.
    
    Raises:
        JWTError: If the token is invalid, expired, or cannot be decoded.
                  (This can be caught by the caller for specific HTTP exceptions)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            # This case should ideally not happen if create_access_token ensures 'sub'
            raise JWTError("Username (sub) missing from token payload.")
        return username
    except JWTError as e:
        # Specific errors like ExpiredSignatureError, InvalidTokenError inherit from JWTError
        # Re-raise to be handled by the calling dependency or endpoint
        raise e

if __name__ == '__main__':
    # Example Usage (primarily for testing the functions directly)
    print("--- Security Module Examples ---")

    # Password Hashing
    plain_pw = "safT_Password123!"
    hashed_pw = get_password_hash(plain_pw)
    print(f"Plain Password: {plain_pw}")
    print(f"Hashed Password: {hashed_pw}")
    print(f"Verification (correct): {verify_password(plain_pw, hashed_pw)}")
    print(f"Verification (incorrect): {verify_password('wrong_password', hashed_pw)}")

    # Token Creation
    user_data = {"sub": "testuser@example.com"} # 'sub' is standard for subject (username)
    try:
        token = create_access_token(user_data)
        print(f"\nGenerated Token for {user_data['sub']}: {token}")

        # Token Decoding
        decoded_username = decode_token_for_username(token)
        print(f"Decoded Username from token: {decoded_username}")
        if decoded_username == user_data["sub"]:
            print("Token creation and decoding successful.")
        else:
            print("Token decoding FAILED or username mismatch.")

    except ValueError as ve:
        print(f"Error during token creation example: {ve}")
    except JWTError as e:
        print(f"Error during token decoding example: {e}")

    # Example of an expired token (requires manipulating time or a very short expiry)
    try:
        expired_token = create_access_token(user_data, expires_delta=timedelta(seconds=-1))
        print(f"\nGenerated Expired Token: {expired_token}")
        decode_token_for_username(expired_token) # This should raise ExpiredSignatureError
    except jwt.ExpiredSignatureError:
        print("Correctly caught ExpiredSignatureError for expired token.")
    except Exception as e:
        print(f"Unexpected error with expired token test: {e}")

    # Example of an invalid token
    invalid_token_string = "this.is.not.a.valid.token"
    try:
        decode_token_for_username(invalid_token_string)
    except JWTError as e: # Catches various JWT errors like InvalidTokenError
        print(f"\nCorrectly caught JWTError for invalid token string: {type(e).__name__}")

    print("\n--- End of Security Module Examples ---")
