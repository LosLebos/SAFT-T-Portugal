import unittest
import os
from typing import Generator, Type
from sqlmodel import SQLModel, create_engine, Session, Field
from sqlalchemy.exc import IntegrityError


# Assuming database.py and models.py are structured to be importable.
# If they are in the parent directory or a src directory:
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import create_db_and_tables as global_create_db_and_tables, get_session as global_get_session
from models import Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel
# Also import underlying Pydantic structures if needed for creating test instances
from models import CustomerAddressStructure, AddressStructure, CustomsDetails, SAFPTGLAccountID, ProductTypeEnum, GroupingCategoryEnum, SAFmonetaryType

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Store the original engine from database.py to restore it later if necessary,
# though for testing, we'll mostly use the test_engine.
original_db_engine = None # Placeholder

def override_get_session() -> Generator[Session, None, None]:
    """Override for get_session to use the test database engine."""
    with Session(test_engine) as session:
        yield session
        # No commit here, tests will handle their own commits/rollbacks as needed.

def setup_test_db():
    """Creates all tables in the in-memory database."""
    # Ensure all SQLModel table classes are known to SQLModel.metadata
    # This happens when models.py is imported and classes inheriting SQLModel are defined.
    SQLModel.metadata.create_all(test_engine)

def teardown_test_db():
    """Drops all tables from the in-memory database."""
    SQLModel.metadata.drop_all(test_engine)


class TestDatabaseOperations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Override the engine used by global get_session if it's directly used by other modules being tested.
        # For create_db_and_tables, we call it directly with test_engine if it supports an engine param,
        # or ensure SQLModel.metadata is populated and call create_all on test_engine.
        
        # The create_db_and_tables in database.py uses a global engine.
        # For isolated testing, it's better if create_db_and_tables could accept an engine.
        # Since it doesn't, we rely on SQLModel.metadata being populated by importing models.py,
        # and then we call create_all directly on our test_engine.
        pass

    def setUp(self):
        """Called before each test method."""
        setup_test_db() # Create tables for each test for isolation

    def tearDown(self):
        """Called after each test method."""
        teardown_test_db() # Drop tables after each test

    def test_create_db_and_tables_run(self):
        """Test that create_db_and_tables (on test engine) runs without error."""
        # This test implicitly checks if SQLModel.metadata is populated correctly
        # by the time create_db_and_tables (or our setup_test_db) is called.
        try:
            # We already called setup_test_db() in setUp, which does this.
            # To be more explicit for *this* test's purpose:
            teardown_test_db() # Clear
            SQLModel.metadata.create_all(test_engine) # Try again
            # A simple query to check if a known table exists could be added here.
            # For example, try to query Customer table.
            with Session(test_engine) as session:
                session.query(Customer).all() # Should not raise if table exists
        except Exception as e:
            self.fail(f"create_db_and_tables (via setup_test_db) failed: {e}")

    def test_save_and_retrieve_customer(self):
        # Dummy address data for Customer
        billing_addr_data = CustomerAddressStructure(
            AddressDetail="123 Test St", City="Testville", PostalCode="T123", Country="PT"
        )
        customer_data = Customer(
            CustomerID="CUST001",
            AccountID="ACC001", # Valid SAFPTGLAccountID
            CustomerTaxID="PT501234567",
            CompanyName="Test Customer Ltd",
            BillingAddress=billing_addr_data, # SQLModel will store this as JSON
            SelfBillingIndicator=0
        )
        
        with Session(test_engine) as session:
            session.add(customer_data)
            session.commit()
            session.refresh(customer_data) # To get DB assigned ID and confirm data
            
            retrieved_customer = session.get(Customer, customer_data.id)
        
        self.assertIsNotNone(retrieved_customer)
        self.assertEqual(retrieved_customer.CustomerID, "CUST001")
        self.assertEqual(retrieved_customer.CompanyName, "Test Customer Ltd")
        self.assertEqual(retrieved_customer.BillingAddress.City, "Testville")
        self.assertIsNotNone(retrieved_customer.id)

    def test_save_and_retrieve_supplier(self):
        billing_addr_data = AddressStructure(
            AddressDetail="456 Supplier Ave", City="Supply City", PostalCode="S456", Country="US"
        )
        supplier_data = Supplier(
            SupplierID="SUPP001",
            AccountID="ACC002",
            SupplierTaxID="US123456789",
            CompanyName="Test Supplier Inc",
            BillingAddress=billing_addr_data
        )
        with Session(test_engine) as session:
            session.add(supplier_data)
            session.commit()
            session.refresh(supplier_data)
            retrieved_supplier = session.get(Supplier, supplier_data.id)

        self.assertIsNotNone(retrieved_supplier)
        self.assertEqual(retrieved_supplier.SupplierID, "SUPP001")
        self.assertEqual(retrieved_supplier.BillingAddress.City, "Supply City")

    def test_save_and_retrieve_product(self):
        customs_data = CustomsDetails(CNCode=["12345678"], UNNumber=["1111"])
        product_data = Product(
            ProductType=ProductTypeEnum.P, # Assuming 'P' is a valid enum value
            ProductCode="PROD001",
            ProductDescription="Test Product Alpha",
            ProductNumberCode="PN001A",
            CustomsDetails=customs_data
        )
        with Session(test_engine) as session:
            session.add(product_data)
            session.commit()
            session.refresh(product_data)
            retrieved_product = session.get(Product, product_data.id)

        self.assertIsNotNone(retrieved_product)
        self.assertEqual(retrieved_product.ProductCode, "PROD001")
        self.assertEqual(retrieved_product.CustomsDetails.UNNumber[0], "1111")


    def test_save_and_retrieve_general_ledger_account(self):
        gl_account_data = GeneralLedgerAccountSQLModel(
            AccountID="101010", # Valid SAFPTGLAccountID
            AccountDescription="Cash and Bank",
            OpeningDebitBalance=Decimal("1000.00"),
            OpeningCreditBalance=Decimal("0.00"),
            ClosingDebitBalance=Decimal("1200.00"),
            ClosingCreditBalance=Decimal("0.00"),
            GroupingCategory=GroupingCategoryEnum.GM, # Valid enum
            TaxonomyCode=111 # Valid SAFPTTaxonomyCode
        )
        with Session(test_engine) as session:
            session.add(gl_account_data)
            session.commit()
            session.refresh(gl_account_data)
            retrieved_account = session.get(GeneralLedgerAccountSQLModel, gl_account_data.id)

        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account.AccountID, "101010")
        self.assertEqual(retrieved_account.GroupingCategory, "GM")
        self.assertEqual(retrieved_account.OpeningDebitBalance, Decimal("1000.00"))
        
    def test_unique_constraint_customer_id(self):
        """Test unique constraint on Customer.CustomerID."""
        addr = CustomerAddressStructure(AddressDetail="Addr", City="City", PostalCode="123", Country="PT")
        c1 = Customer(CustomerID="UNIQUE01", AccountID="ACC1", CustomerTaxID="NIF1", CompanyName="C1", BillingAddress=addr)
        c2_dup = Customer(CustomerID="UNIQUE01", AccountID="ACC2", CustomerTaxID="NIF2", CompanyName="C2", BillingAddress=addr)

        with Session(test_engine) as session:
            session.add(c1)
            session.commit()
            
            session.add(c2_dup)
            with self.assertRaises((IntegrityError, Exception)): # SQLite raises IntegrityError, others might vary
                session.commit() # This should fail due to unique constraint violation

if __name__ == '__main__':
    unittest.main()
