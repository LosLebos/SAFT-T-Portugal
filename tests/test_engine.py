import unittest
import os
import json
import csv
import logging
from typing import Dict, Type

from sqlmodel import SQLModel, Session, create_engine, Field
from pydantic import BaseModel # For type hinting if some non-SQLModels are involved

# Adjust import paths as necessary
from engine import process_and_store_file, ensure_db_initialized # Updated function name
from models import Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel # Import SQLModel versions
from models import CustomerAddressStructure # For constructing test data
from database import DATABASE_URL, get_session as original_get_session, create_db_and_tables as original_create_db_and_tables

# Disable most logging unless debugging
# logging.disable(logging.CRITICAL) # Keep logs for engine tests for now

# --- Test Database Setup ---
TEST_DB_FILE = "test_engine_saft_data.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
test_engine = None # Will be initialized in setUpClass

def override_get_session_for_engine_tests() -> Session:
    """Overrides database.get_session to use the test engine."""
    global test_engine
    if test_engine is None:
        raise Exception("Test engine not initialized. Call setup_test_engine first.")
    with Session(test_engine) as session:
        yield session
        # Tests should manage their own commit/rollback for clarity,
        # but a default commit here might be okay for simple tests.
        # For now, let process_and_store_file handle its own session commits.

original_engine_in_database_module = None
original_get_session_in_database_module = None

class TestEngineWithDatabase(unittest.TestCase):

    sample_dir = "test_engine_db_sample_data"
    csv_file_path = os.path.join(sample_dir, "sample_customers.csv")
    mapping_file_path = os.path.join(sample_dir, "sample_mapping.json")
    
    # Using actual SQLModel classes from models.py
    test_saft_sqlmodel_registry: Dict[str, Type[SQLModel]] = {
        "Customer": Customer,
        "Supplier": Supplier,
        "Product": Product,
        "GeneralLedgerAccount": GeneralLedgerAccountSQLModel,
    }

    @classmethod
    def setUpClass(cls):
        global test_engine, original_engine_in_database_module, original_get_session_in_database_module
        global _db_initialized_in_engine # Access the flag in engine.py
        
        # 1. Setup Test Engine for SQLite (file-based for inspection, in-memory is also an option)
        test_engine = create_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
        
        # 2. Override database module's engine and get_session for the duration of these tests
        # This is a common way to patch dependencies for testing.
        import database as db_module # Import the module itself to patch its globals
        original_engine_in_database_module = db_module.engine
        original_get_session_in_database_module = db_module.get_session
        
        db_module.engine = test_engine
        db_module.get_session = override_get_session_for_engine_tests

        # 3. Reset the _db_initialized flag in engine.py so ensure_db_initialized runs with test_engine
        import engine as engine_module
        engine_module._db_initialized = False # Reset initialization flag in engine
        
        # 4. Create directory for sample files
        if not os.path.exists(cls.sample_dir):
            os.makedirs(cls.sample_dir)

        # 5. Create Sample CSV
        cls.sample_csv_rows = [
            {"Client ID": "C100", "Company Name": "DB Test Corp 1", "Address": "1 DB St", "Town": "DBville", "PostCode": "DB1", "Nation": "PT", "NIF": "PT000000100", "Account": "ACCDB100", "SelfBill": "0"},
            {"Client ID": "C200", "Company Name": "DB Test Corp 2", "Address": "2 DB Rd", "Town": "DBburg", "PostCode": "DB2", "Nation": "US", "NIF": "US000000200", "Account": "Desconhecido", "SelfBill": "1"},
            {"Client ID": "C300", "Company Name": "DB Incomplete", "Address": "3 DB Ln", "Town": "NodataDB", "PostCode": "DB3", "Nation": "GB", "NIF": "", "Account": "ACCDB300", "SelfBill": "0"}, # Empty NIF
        ]
        with open(cls.csv_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cls.sample_csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(cls.sample_csv_rows)

        # 6. Create Sample Mapping Profile
        cls.sample_mapping_config = {
            "profile_name": "Engine DB Test Customer Mapping",
            "target_model": "Customer", # Target model is Customer
            "mappings": {
                "Client ID": "CustomerID", "Company Name": "CompanyName",
                "Address": "BillingAddress.AddressDetail", "Town": "BillingAddress.City",
                "PostCode": "BillingAddress.PostalCode", "Nation": "BillingAddress.Country",
                "NIF": "CustomerTaxID", "Account": "AccountID", "SelfBill": "SelfBillingIndicator"
            }
        }
        with open(cls.mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump(cls.sample_mapping_config, f)
            
        # 7. Ensure tables are created in the test DB via the engine's mechanism
        # process_and_store_file calls ensure_db_initialized, which calls create_db_and_tables
        # using the (now overridden) database.engine.
        # No explicit call to original_create_db_and_tables(test_engine) is needed if patching is correct.

    @classmethod
    def tearDownClass(cls):
        global original_engine_in_database_module, original_get_session_in_database_module
        import database as db_module
        
        # Restore original engine and get_session in database.py
        db_module.engine = original_engine_in_database_module
        db_module.get_session = original_get_session_in_database_module
        
        # Clean up sample files and directory
        if os.path.exists(cls.csv_file_path): os.remove(cls.csv_file_path)
        if os.path.exists(cls.mapping_file_path): os.remove(cls.mapping_file_path)
        if os.path.exists(cls.sample_dir): os.rmdir(cls.sample_dir)
        if os.path.exists(TEST_DB_FILE): os.remove(TEST_DB_FILE) # Remove test DB file

    def setUp(self):
        """Clear table data before each test, but keep tables."""
        global test_engine
        # We need to ensure tables exist, but old data is cleared.
        # ensure_db_initialized in process_and_store_file will create tables if they don't exist.
        # For test isolation, clearing data is better.
        SQLModel.metadata.drop_all(test_engine) # Drop all
        SQLModel.metadata.create_all(test_engine) # Recreate for a clean slate
        
        # Also reset the engine's _db_initialized flag before each test run
        # to ensure ensure_db_initialized in engine.py runs its course with the patched DB.
        import engine as engine_module
        engine_module._db_initialized = False


    def test_process_and_store_file_success_check_db(self):
        """Test successful processing and storage, then verify data in DB."""
        
        # process_and_store_file now uses the patched get_session and engine
        results = process_and_store_file(
            self.csv_file_path,
            self.mapping_file_path,
            self.test_saft_sqlmodel_registry
        )
        
        # Expect 2 successful instances, row 3 (C300) should fail due to NIF (CustomerTaxID) being mandatory
        # and provided as None/empty string which SAFPTtextTypeMandatoryMax30Car does not allow if min_length=1.
        self.assertEqual(len(results), 2, "Should process 2 customers successfully, 1 should fail validation.")

        # Verify data in the database
        with Session(test_engine) as session:
            stored_customers = session.query(Customer).all()
            self.assertEqual(len(stored_customers), 2)

            # Verify C100
            c100_db = session.query(Customer).filter(Customer.CustomerID == "C100").first()
            self.assertIsNotNone(c100_db)
            self.assertEqual(c100_db.CompanyName, "DB Test Corp 1")
            self.assertEqual(c100_db.CustomerTaxID, "PT000000100")
            self.assertIsInstance(c100_db.BillingAddress, CustomerAddressStructure) # SQLModel deserializes JSON to Pydantic model
            self.assertEqual(c100_db.BillingAddress.AddressDetail, "1 DB St")
            self.assertEqual(c100_db.BillingAddress.City, "DBville")
            self.assertEqual(c100_db.BillingAddress.PostalCode, "DB1")
            self.assertEqual(c100_db.BillingAddress.Country, "PT")
            self.assertEqual(c100_db.AccountID, "ACCDB100")
            self.assertEqual(c100_db.SelfBillingIndicator, 0)

            # Verify C200
            c200_db = session.query(Customer).filter(Customer.CustomerID == "C200").first()
            self.assertIsNotNone(c200_db)
            self.assertEqual(c200_db.CompanyName, "DB Test Corp 2")
            self.assertEqual(c200_db.CustomerTaxID, "US000000200")
            self.assertEqual(c200_db.AccountID, "Desconhecido")
            self.assertEqual(c200_db.SelfBillingIndicator, 1)
            
            # Verify C300 (with empty NIF) was not stored due to validation error
            c300_db = session.query(Customer).filter(Customer.CustomerID == "C300").first()
            self.assertIsNone(c300_db, "C300 should not be in the database due to validation error for empty NIF.")

    def test_process_and_store_file_csv_not_found(self):
        # logging.disable(logging.NOTSET) # Enable logs if needed for debugging
        with self.assertLogs(logger='engine', level='ERROR') as log_watcher:
            results = process_and_store_file(
                "non_existent.csv",
                self.mapping_file_path,
                self.test_saft_sqlmodel_registry
            )
        logging.disable(logging.CRITICAL)
        self.assertEqual(len(results), 0)
        self.assertTrue(any("File not found" in record.getMessage() and "non_existent.csv" in record.getMessage() for record in log_watcher.records))

    def test_process_and_store_file_mapping_not_found(self):
        # logging.disable(logging.NOTSET)
        with self.assertLogs(logger='engine', level='ERROR') as log_watcher:
            results = process_and_store_file(
                self.csv_file_path,
                "non_existent_mapping.json",
                self.test_saft_sqlmodel_registry
            )
        logging.disable(logging.CRITICAL)
        self.assertEqual(len(results), 0)
        self.assertTrue(any("File not found" in record.getMessage() and "non_existent_mapping.json" in record.getMessage() for record in log_watcher.records))

    def test_process_and_store_file_target_model_not_in_registry(self):
        bad_mapping_config = self.sample_mapping_config.copy()
        bad_mapping_config["target_model"] = "UnknownModel"
        bad_mapping_file_path = os.path.join(self.sample_dir, "bad_mapping.json")
        with open(bad_mapping_file_path, 'w') as f:
            json.dump(bad_mapping_config, f)

        # logging.disable(logging.NOTSET)
        with self.assertLogs(logger='engine', level='ERROR') as log_watcher: 
            results = process_and_store_file(
                self.csv_file_path,
                bad_mapping_file_path,
                self.test_saft_sqlmodel_registry
            )
        logging.disable(logging.CRITICAL)
        self.assertEqual(len(results), 0)
        self.assertTrue(any("Target model 'UnknownModel' not found" in record.getMessage() for record in log_watcher.records))
        
        os.remove(bad_mapping_file_path)

        logging.disable(logging.CRITICAL)
        self.assertEqual(len(results), 0)
        self.assertTrue(any("No data found in CSV file" in record.getMessage() and "empty.csv" in record.getMessage() for record in log_watcher.records))
        os.remove(empty_csv_path)


# --- Tests for XML Generation and Validation Flow in Engine ---
from models import (User, AuditFile, Header, MasterFiles, GeneralLedgerEntries, Journal, Transaction, Lines, DebitLine, CreditLine,
                    SAFPTDateSpan, AddressStructure, AuditFileVersion, CompanyIDType, SAFPTPortugueseVatNumber,
                    TaxAccountingBasisEnum, CurrencyPT, ProductIDType, SAFPTGLAccountID, SAFPTAccountingPeriod,
                    TransactionTypeEnum, SAFdateTimeType, SAFmonetaryType, ProductTypeEnum, CustomerAddressStructure) # Added User, ProductTypeEnum, CustomerAddressStructure
from decimal import Decimal
from core.config import DEMO_USER_USERNAME # For creating a demo user
from core.security import get_password_hash # For creating user

# Path to XSD for these tests - assuming it's locatable from the test execution context
# This mirrors the logic in test_xsd_validator.py for finding the XSD.
XSD_FILE_PATH_FOR_ENGINE_TESTS = os.path.join(os.path.dirname(__file__), '..', "SAFTPT1_04_01.xsd")
if not os.path.exists(XSD_FILE_PATH_FOR_ENGINE_TESTS):
    XSD_FILE_PATH_FOR_ENGINE_TESTS = "SAFTPT1_04_01.xsd"


@unittest.skipIf(not os.path.exists(XSD_FILE_PATH_FOR_ENGINE_TESTS), f"XSD file not found at {XSD_FILE_PATH_FOR_ENGINE_TESTS}, skipping engine XML validation tests.")
class TestEngineXmlGenerationValidation(unittest.TestCase): # Renamed to avoid conflict with TestEngineWithDatabase
    
    # This test class will also need its own DB setup if get_full_audit_data_for_xml is to be tested live.
    # It uses the same DB file and engine name as TestEngineWithDatabase, which might cause issues if run in parallel
    # or if state is not properly managed. For sequential unittest, it's usually fine.
    # Alternatively, mock the db_session for get_full_audit_data_for_xml.
    # For now, let's assume it uses the same test_engine setup as TestEngineWithDatabase.
    # This requires this class to also patch the database.engine and database.get_session.

    @classmethod
    def setUpClass(cls):
        global test_engine # Re-use from TestEngineWithDatabase or define a new one
        if test_engine is None: # If tests run separately, test_engine might not be init
            test_engine = create_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
        
        import database as db_module
        cls.original_engine = db_module.engine
        cls.original_get_session = db_module.get_session
        db_module.engine = test_engine
        db_module.get_session = override_get_session_for_engine_tests # Defined in TestEngineWithDatabase

        import engine as engine_module # Reset engine's DB init flag
        engine_module._db_initialized = False


    @classmethod
    def tearDownClass(cls):
        import database as db_module
        db_module.engine = cls.original_engine
        db_module.get_session = cls.original_get_session
        # DB file cleanup is handled by TestEngineWithDatabase.tearDownClass if it runs last.
        # If this class runs independently, it might need its own DB file cleanup.

    def setUp(self):
        SQLModel.metadata.drop_all(test_engine) # Clear data
        SQLModel.metadata.create_all(test_engine) # Create tables
        import engine as engine_module # Reset engine's DB init flag
        engine_module._db_initialized = False


    def _create_user_for_test(self, session: Session, username: str, is_demo: bool = False) -> User:
        user = User(
            username=username,
            hashed_password=get_password_hash("testpassword"),
            email=f"{username}@example.com",
            is_active=True,
            is_superuser=False
        )
        if is_demo and username == DEMO_USER_USERNAME:
            # Specific attributes for demo user if any, like a known ID or different email.
            pass
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def _populate_specific_user_data(self, session: Session, user: User):
        """Populates some data owned by the given user."""
        cust_addr = CustomerAddressStructure(AddressDetail=f"Street for {user.username}", City="UserCity", PostalCode="00000", Country="PT")
        customer = Customer(
            CustomerID=f"CUST_{user.username.upper()}", AccountID=SAFPTGLAccountID(f"211{user.id}"),
            CustomerTaxID=f"PT501{user.id:06d}", CompanyName=f"{user.username} Corp.",
            BillingAddress=cust_addr, owner_id=user.id
        )
        session.add(customer)
        # Add other data (Product, Supplier, Account) - these are global in current model
        # So only add if they don't exist to avoid conflicts between tests / users
        if not session.exec(select(Product).where(Product.ProductCode == "P_GLOBAL")).first():
            prod = Product(ProductType=ProductTypeEnum.P, ProductCode="P_GLOBAL", ProductDescription="Global Product", ProductNumberCode="PN_GLOBAL")
            session.add(prod)
        session.commit()


    def test_get_full_audit_data_for_xml_with_owner_filtering(self):
        from engine import get_full_audit_data_for_xml # Import here to use patched DB
        
        with Session(test_engine) as session:
            demo_user = self._create_user_for_test(session, DEMO_USER_USERNAME, is_demo=True)
            self._populate_specific_user_data(session, demo_user) # Demo user data
            
            actual_user = self._create_user_for_test(session, "actual_user")
            self._populate_specific_user_data(session, actual_user) # Actual user data
            
            # Test for Demo User
            audit_file_demo = get_full_audit_data_for_xml(session, demo_user)
            self.assertEqual(audit_file_demo.Header.CompanyName, "Demo Company SA (SAF-T View)")
            self.assertTrue(len(audit_file_demo.MasterFiles.Customer) == 1)
            self.assertEqual(audit_file_demo.MasterFiles.Customer[0].CustomerID, f"CUST_{DEMO_USER_USERNAME.upper()}")

            # Test for Actual User
            audit_file_actual = get_full_audit_data_for_xml(session, actual_user)
            self.assertEqual(audit_file_actual.Header.CompanyName, f"{actual_user.username}'s Company")
            self.assertTrue(len(audit_file_actual.MasterFiles.Customer) == 1)
            self.assertEqual(audit_file_actual.MasterFiles.Customer[0].CustomerID, f"CUST_{actual_user.username.upper()}")
            
            # Ensure global data (like products) is present for both
            self.assertTrue(len(audit_file_demo.MasterFiles.Product) >= 1)
            self.assertTrue(len(audit_file_actual.MasterFiles.Product) >= 1)
            self.assertEqual(audit_file_demo.MasterFiles.Product[0].ProductCode, audit_file_actual.MasterFiles.Product[0].ProductCode)


    def test_generate_and_validate_saft_file_success_with_engine_data(self):
        from engine import generate_and_validate_saft_file, get_full_audit_data_for_xml
        
        with Session(test_engine) as session:
            user = self._create_user_for_test(session, "engine_valid_user")
            self._populate_specific_user_data(session, user) # Populate some data for this user
            
            audit_file_instance = get_full_audit_data_for_xml(session, user)
            # Ensure the instance has enough data to be XSD valid (especially mandatory MasterFiles elements)
            if not audit_file_instance.MasterFiles.Product: # Add a product if none from populate
                 audit_file_instance.MasterFiles.Product = [Product(ProductType=ProductTypeEnum.S, ProductCode="SERVENG", ProductDescription="Service Engine", ProductNumberCode="SRENG")]
            if not audit_file_instance.MasterFiles.GeneralLedgerAccounts or not audit_file_instance.MasterFiles.GeneralLedgerAccounts.Account:
                from models import GeneralLedgerAccounts, Account as GLAccount, GroupingCategoryEnum
                audit_file_instance.MasterFiles.GeneralLedgerAccounts = GeneralLedgerAccounts(
                    TaxonomyReference="S",
                    Account=[GLAccount(AccountID="111TESTENG", AccountDescription="Cash Test", OpeningDebitBalance=0, OpeningCreditBalance=0, ClosingDebitBalance=0, ClosingCreditBalance=0, GroupingCategory=GroupingCategoryEnum.GM)]
                )


            xml_string, errors = generate_and_validate_saft_file(audit_file_instance, XSD_FILE_PATH_FOR_ENGINE_TESTS)

            self.assertIsNotNone(xml_string, f"XML string should be generated. Errors: {errors}")
            self.assertEqual(len(errors), 0, f"Validation should pass. Errors: {errors}\nXML: {xml_string[:1000] if xml_string else ''}")
            if xml_string: # Avoid error if None
                self.assertTrue(xml_string.startswith("<?xml version=\"1.0\" encoding=\"utf-8\"?>"))
                self.assertIn(f"<CompanyName>{user.username}'s Company</CompanyName>", xml_string)

    def test_generate_and_validate_saft_file_invalid_data_from_engine(self):
        from engine import generate_and_validate_saft_file, get_full_audit_data_for_xml
        
        with Session(test_engine) as session:
            user = self._create_user_for_test(session, "engine_invalid_user")
            self._populate_specific_user_data(session, user) # Populate some data
            
            audit_file_instance = get_full_audit_data_for_xml(session, user)
            audit_file_instance.Header.FiscalYear = "INVALID_YEAR_FOR_XSD" # type: ignore
        
            xml_string, errors = generate_and_validate_saft_file(audit_file_instance, XSD_FILE_PATH_FOR_ENGINE_TESTS)

            self.assertIsNone(xml_string, "XML string should be None when validation fails.")
            self.assertTrue(len(errors) > 0, "Error list should not be empty for invalid data.")
            self.assertTrue(any("INVALID_YEAR_FOR_XSD" in error for error in errors) and \
                            any("integer" in error for error in errors),
                            f"Expected FiscalYear validation error not found in {errors}")


if __name__ == '__main__':
    # Ensure tests can find other .py files (engine, models, mapping, uploader)
    # This is more for local execution convenience.
    current_script_dir = os.path.dirname(__file__)
    # Assuming all source .py files are in the parent directory of 'tests' or same directory
    # If tests/ is a subdir of the project root where other .py files are:
    project_root = os.path.abspath(os.path.join(current_script_dir, '..')) 
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # If all files are flat in one dir (like the tool might do):
    if current_script_dir not in sys.path:
         sys.path.insert(0, current_script_dir)

    unittest.main()
