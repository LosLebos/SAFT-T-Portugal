import unittest
import os
import sys
from pathlib import Path
from typing import Generator

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from jose import jwt # For checking token content if needed, not for decoding in tests usually

# --- Add project root to sys.path ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app # FastAPI app instance
from database import get_session as original_get_session
from models import User # User SQLModel
from schemas import user_schemas # For request/response validation if needed
from core.security import ALGORITHM, SECRET_KEY # To inspect token content if necessary

# --- Test Database Setup ---
TEST_DB_FILE_AUTH = "test_auth_saft_data.db"
TEST_DATABASE_URL_AUTH = f"sqlite:///{TEST_DB_FILE_AUTH}"
test_auth_engine = None

def override_get_session_for_auth_tests() -> Generator[Session, None, None]:
    global test_auth_engine
    if test_auth_engine is None:
        raise Exception("Test Auth engine not initialized.")
    with Session(test_auth_engine) as session:
        yield session

class TestAuthEndpoints(unittest.TestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        global test_auth_engine
        test_auth_engine = create_engine(TEST_DATABASE_URL_AUTH, echo=False, connect_args={"check_same_thread": False})
        
        # Override the get_session dependency for the FastAPI app
        app.dependency_overrides[original_get_session] = override_get_session_for_auth_tests
        
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear() # Clear overrides
        if os.path.exists(TEST_DB_FILE_AUTH):
            os.remove(TEST_DB_FILE_AUTH)

    def setUp(self):
        """Create tables before each test for isolation."""
        SQLModel.metadata.create_all(test_auth_engine)

    def tearDown(self):
        """Drop tables after each test."""
        SQLModel.metadata.drop_all(test_auth_engine)

    def test_user_registration_success(self):
        response = self.client.post(
            "/auth/register",
            json={"username": "testuser1", "email": "testuser1@example.com", "password": "TestPassword123!"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["username"], "testuser1")
        self.assertEqual(data["email"], "testuser1@example.com")
        self.assertTrue(data["is_active"])
        self.assertFalse(data["is_superuser"])
        self.assertIn("id", data)

        # Verify user in DB (optional, but good for full check)
        with Session(test_auth_engine) as session:
            user_in_db = session.get(User, data["id"])
            self.assertIsNotNone(user_in_db)
            self.assertEqual(user_in_db.username, "testuser1")

    def test_user_registration_duplicate_username(self):
        self.client.post(
            "/auth/register",
            json={"username": "dupuser", "email": "dupuser1@example.com", "password": "Password123"}
        ) # First registration
        response = self.client.post(
            "/auth/register",
            json={"username": "dupuser", "email": "dupuser2@example.com", "password": "Password456"}
        ) # Attempt duplicate username
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("Username already registered", response.json()["detail"])

    def test_user_registration_duplicate_email(self):
        self.client.post(
            "/auth/register",
            json={"username": "emailuser1", "email": "common@example.com", "password": "Password123"}
        )
        response = self.client.post(
            "/auth/register",
            json={"username": "emailuser2", "email": "common@example.com", "password": "Password456"}
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("Email already registered", response.json()["detail"])

    def test_login_for_access_token_success(self):
        # 1. Register user first
        reg_response = self.client.post(
            "/auth/register",
            json={"username": "loginuser", "email": "login@example.com", "password": "LoginPassword123"}
        )
        self.assertEqual(reg_response.status_code, 200)

        # 2. Attempt login
        login_response = self.client.post(
            "/auth/token",
            data={"username": "loginuser", "password": "LoginPassword123"} # Form data
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        token_data = login_response.json()
        self.assertIn("access_token", token_data)
        self.assertEqual(token_data["token_type"], "bearer")
        
        # Optionally decode token to verify subject (username)
        # This is more of a test for security.create_access_token if not done elsewhere
        decoded_token = jwt.decode(token_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        self.assertEqual(decoded_token["sub"], "loginuser")


    def test_login_for_access_token_incorrect_password(self):
        self.client.post(
            "/auth/register",
            json={"username": "authfailuser", "password": "CorrectPassword"}
        )
        response = self.client.post(
            "/auth/token",
            data={"username": "authfailuser", "password": "WrongPassword"}
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertIn("Incorrect username or password", response.json()["detail"])

    def test_login_for_access_token_user_not_found(self):
        response = self.client.post(
            "/auth/token",
            data={"username": "nosuchloginuser", "password": "AnyPassword"}
        )
        self.assertEqual(response.status_code, 401, response.text) # Or 404 depending on desired ambiguity
        self.assertIn("Incorrect username or password", response.json()["detail"]) # Standard for failed login attempt

    def test_read_users_me_success(self):
        # Register and login to get a token
        self.client.post("/auth/register", json={"username": "me_user", "password": "PasswordForMe"})
        login_resp = self.client.post("/auth/token", data={"username": "me_user", "password": "PasswordForMe"})
        token = login_resp.json()["access_token"]

        # Access /users/me with the token
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/auth/users/me", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["username"], "me_user")
        self.assertTrue(data["is_active"]) # Default for new user

    def test_read_users_me_inactive_user(self):
        # Register user
        reg_data = self.client.post("/auth/register", json={"username": "inactive_user", "password": "PasswordInactive"}).json()
        user_id = reg_data["id"]

        # Deactivate user directly in DB for test setup
        with Session(test_auth_engine) as session:
            user_in_db = session.get(User, user_id)
            user_in_db.is_active = False
            session.add(user_in_db)
            session.commit()
        
        # Login to get token
        login_resp = self.client.post("/auth/token", data={"username": "inactive_user", "password": "PasswordInactive"})
        token = login_resp.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/auth/users/me", headers=headers)
        self.assertEqual(response.status_code, 400, response.text) # get_current_active_user raises 400 for inactive
        self.assertIn("Inactive user", response.json()["detail"])


    def test_read_users_me_no_token(self):
        response = self.client.get("/auth/users/me")
        self.assertEqual(response.status_code, 401) # FastAPI's default for missing OAuth2 token
        self.assertIn("Not authenticated", response.json()["detail"])

    def test_read_users_me_invalid_token(self):
        headers = {"Authorization": "Bearer invalidtokenstring"}
        response = self.client.get("/auth/users/me", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Could not validate credentials", response.json()["detail"])


if __name__ == '__main__':
    unittest.main()
