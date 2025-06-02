import unittest
import os
import sys
from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine, select

# --- Add project root to sys.path ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.demo_data import create_demo_user, populate_demo_data
from core.config import DEMO_USER_USERNAME, DEMO_USER_PASSWORD # For verification
from core.security import verify_password # For checking demo user password
from models import User, Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel

# --- Test Database Setup ---
TEST_DB_FILE_DEMO = "test_demo_data.db"
TEST_DATABASE_URL_DEMO = f"sqlite:///{TEST_DB_FILE_DEMO}"
test_demo_engine = None

class TestDemoData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global test_demo_engine
        test_demo_engine = create_engine(TEST_DATABASE_URL_DEMO, echo=False, connect_args={"check_same_thread": False})
        # No app patching needed here as we are testing direct DB functions.

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_FILE_DEMO):
            os.remove(TEST_DB_FILE_DEMO)

    def setUp(self):
        """Create tables before each test for isolation."""
        SQLModel.metadata.create_all(test_demo_engine)

    def tearDown(self):
        """Drop tables after each test."""
        SQLModel.metadata.drop_all(test_demo_engine)

    def test_create_demo_user_new(self):
        """Test creation of a new demo user."""
        with Session(test_demo_engine) as session:
            demo_user = create_demo_user(session)
            self.assertIsNotNone(demo_user)
            self.assertEqual(demo_user.username, DEMO_USER_USERNAME)
            self.assertTrue(verify_password(DEMO_USER_PASSWORD, demo_user.hashed_password))
            self.assertTrue(demo_user.is_active)
            self.assertFalse(demo_user.is_superuser) # Default for create_user

            # Verify it's in the DB
            user_in_db = session.get(User, demo_user.id)
            self.assertIsNotNone(user_in_db)
            self.assertEqual(user_in_db.username, DEMO_USER_USERNAME)

    def test_create_demo_user_existing(self):
        """Test attempting to create demo user when one already exists."""
        with Session(test_demo_engine) as session:
            # First creation
            created_user1 = create_demo_user(session)
            # Second call should return the existing user
            created_user2 = create_demo_user(session)
            
            self.assertEqual(created_user1.id, created_user2.id)
            self.assertEqual(created_user2.username, DEMO_USER_USERNAME)

    def test_create_demo_user_existing_inactive_becomes_active(self):
        """Test that an existing inactive demo user is activated."""
        with Session(test_demo_engine) as session:
            # Manually create an inactive demo user first
            from core.security import get_password_hash
            inactive_demo = User(
                username=DEMO_USER_USERNAME,
                hashed_password=get_password_hash(DEMO_USER_PASSWORD),
                email=f"{DEMO_USER_USERNAME}@example.com",
                is_active=False
            )
            session.add(inactive_demo)
            session.commit()
            session.refresh(inactive_demo)
            self.assertFalse(inactive_demo.is_active)

            # Now call create_demo_user, it should find and activate this user
            activated_demo_user = create_demo_user(session)
            self.assertIsNotNone(activated_demo_user)
            self.assertEqual(activated_demo_user.id, inactive_demo.id)
            self.assertTrue(activated_demo_user.is_active) # Key assertion

            user_in_db = session.get(User, activated_demo_user.id)
            self.assertTrue(user_in_db.is_active)


    def test_populate_demo_data_creates_records(self):
        """Test that demo data is populated for the demo user."""
        with Session(test_demo_engine) as session:
            demo_user = create_demo_user(session)
            self.assertIsNotNone(demo_user, "Demo user must be created first")
            
            populate_demo_data(session, demo_user)

            # Verify Customers linked to demo_user
            customers = session.exec(select(Customer).where(Customer.owner_id == demo_user.id)).all()
            self.assertTrue(len(customers) >= 2, "Should have at least 2 demo customers.")
            for customer in customers:
                self.assertEqual(customer.owner_id, demo_user.id)
                self.assertIn("(Demo)", customer.CompanyName)

            # Verify global Suppliers (as they don't have owner_id)
            suppliers = session.exec(select(Supplier)).all()
            self.assertTrue(len(suppliers) >= 2, "Should have at least 2 global demo suppliers.")
            self.assertIn("(Demo)", suppliers[0].CompanyName)

            # Verify global Products
            products = session.exec(select(Product)).all()
            self.assertTrue(len(products) >= 2, "Should have at least 2 global demo products.")
            self.assertIn("(Demo)", products[0].ProductDescription)

            # Verify global GL Accounts
            gl_accounts = session.exec(select(GeneralLedgerAccountSQLModel)).all()
            self.assertTrue(len(gl_accounts) >= 4, "Should have at least 4 global demo GL accounts.")
            self.assertIn("(Demo)", gl_accounts[0].AccountDescription)

    def test_populate_demo_data_idempotent_for_customers(self):
        """Test that populate_demo_data doesn't duplicate customer demo data."""
        with Session(test_demo_engine) as session:
            demo_user = create_demo_user(session)
            
            # Call populate twice
            populate_demo_data(session, demo_user)
            count_after_first_call = len(session.exec(select(Customer).where(Customer.owner_id == demo_user.id)).all())
            
            populate_demo_data(session, demo_user)
            count_after_second_call = len(session.exec(select(Customer).where(Customer.owner_id == demo_user.id)).all())
            
            self.assertEqual(count_after_first_call, count_after_second_call, 
                             "Customer demo data should not be duplicated on subsequent calls.")
            self.assertTrue(count_after_first_call > 0, "Demo customers should have been created.")

    def test_populate_demo_data_idempotent_for_global_data(self):
        """Test that populate_demo_data doesn't duplicate global demo data (Suppliers, Products, GL Accounts)."""
        with Session(test_demo_engine) as session:
            demo_user = create_demo_user(session) # Needed as populate_demo_data expects it
            
            # Call populate twice
            populate_demo_data(session, demo_user)
            supplier_count1 = len(session.exec(select(Supplier)).all())
            product_count1 = len(session.exec(select(Product)).all())
            gl_account_count1 = len(session.exec(select(GeneralLedgerAccountSQLModel)).all())
            
            populate_demo_data(session, demo_user) # Call again
            supplier_count2 = len(session.exec(select(Supplier)).all())
            product_count2 = len(session.exec(select(Product)).all())
            gl_account_count2 = len(session.exec(select(GeneralLedgerAccountSQLModel)).all())

            self.assertTrue(supplier_count1 > 0, "Demo suppliers should exist.")
            self.assertTrue(product_count1 > 0, "Demo products should exist.")
            self.assertTrue(gl_account_count1 > 0, "Demo GL accounts should exist.")

            self.assertEqual(supplier_count1, supplier_count2, "Global Supplier demo data should not be duplicated.")
            self.assertEqual(product_count1, product_count2, "Global Product demo data should not be duplicated.")
            self.assertEqual(gl_account_count1, gl_account_count2, "Global GL Account demo data should not be duplicated.")


if __name__ == '__main__':
    unittest.main()
