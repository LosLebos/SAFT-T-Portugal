from passlib.context import CryptContext

# --- Password Hashing ---
# Use bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)


if __name__ == '__main__':
    # Example Usage (primarily for testing the functions directly)
    print("--- Security Module Examples (Password Hashing Only) ---")

    # Password Hashing
    plain_pw = "safT_Password123!"
    hashed_pw = get_password_hash(plain_pw)
    print(f"Plain Password: {plain_pw}")
    print(f"Hashed Password: {hashed_pw}")
    print(f"Verification (correct): {verify_password(plain_pw, hashed_pw)}")
    print(f"Verification (incorrect): {verify_password('wrong_password', hashed_pw)}")

    print("\n--- End of Security Module Examples ---")
