import unittest
import os
import sys
from pathlib import Path
from typing import Generator, Optional

from sqlmodel import SQLModel, Session, create_engine, select, Field
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine import get_full_audit_data_for_xml, generate_and_validate_saft_file
from models import (
    User, Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel,
    AuditFile, Header, MasterFiles, GeneralLedgerAccounts, GeneralLedgerEntries, Journal, Transaction, Lines, DebitLine, CreditLine,
    CustomerAddressStructure, AddressStructure, ProductTypeEnum, SAFPTGLAccountID,
    SAFPTDateSpan, TaxAccountingBasisEnum, CurrencyPT, GroupingCategoryEnum,
    TransactionTypeEnum, SAFPTAccountingPeriod, SAFdateTimeType, SAFmonetaryType
)
from core.config import DEMO_USER_USERNAME
from core.demo_data import create_demo_user as core_create_demo_user, populate_demo_data as core_populate_demo_data

TEST_DB_FILE_ENGINE = "test_engine_module_data.db"
TEST_DATABASE_URL_ENGINE = f"sqlite:///{TEST_DB_FILE_ENGINE}"
test_engine_module_engine = None 

original_db_engine_for_engine_test = None
original_get_session_for_engine_test = None

def override_get_session_for_engine_module_tests() -> Generator[Session, None, None]:
    global test_engine_module_engine
    if test_engine_module_engine is None:
        raise Exception("Test Engine (for engine.py tests) not initialized.")
    with Session(test_engine_module_engine) as session:
        yield session

XSD_FILE_PATH_FOR_ENGINE_TESTS = PROJECT_ROOT / "SAFTPT1_04_01.xsd"

class TestEngineFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global test_engine_module_engine, original_db_engine_for_engine_test, original_get_session_for_engine_test
        
        test_engine_module_engine = create_engine(TEST_DATABASE_URL_ENGINE, echo=False, connect_args={"check_same_thread": False})
        
        import database as db_module
        original_db_engine_for_engine_test = db_module.engine
        original_get_session_for_engine_test = db_module.get_session
        db_module.engine = test_engine_module_engine
        db_module.get_session = override_get_session_for_engine_module_tests

        import engine as engine_module
        if hasattr(engine_module, '_db_initialized'): 
            engine_module._db_initialized = False 
            engine_module.ensure_db_initialized() 

        if not XSD_FILE_PATH_FOR_ENGINE_TESTS.exists():
            print(f"Warning: XSD file not found at {XSD_FILE_PATH_FOR_ENGINE_TESTS}. Some XML validation tests might be skipped.")

    @classmethod
    def tearDownClass(cls):
        import database as db_module
        db_module.engine = original_db_engine_for_engine_test
        db_module.get_session = original_get_session_for_engine_test
        
        if os.path.exists(TEST_DB_FILE_ENGINE):
            os.remove(TEST_DB_FILE_ENGINE)

    def setUp(self):
        SQLModel.metadata.drop_all(test_engine_module_engine) 
        SQLModel.metadata.create_all(test_engine_module_engine) 
        import engine as engine_module 
        if hasattr(engine_module, '_db_initialized'):
             engine_module._db_initialized = False
        # Setup demo user and their data for each test
        with Session(test_engine_module_engine) as session:
            self.demo_user = core_create_demo_user(session)
            core_populate_demo_data(session, self.demo_user)
            session.refresh(self.demo_user)


    def tearDown(self):
        SQLModel.metadata.drop_all(test_engine_module_engine)


    def test_get_full_audit_data_for_xml_demo_user_context(self):
        with Session(test_engine_module_engine) as session:
            # Demo user and data are already populated by setUp
            demo_user_from_db = session.exec(select(User).where(User.username == DEMO_USER_USERNAME)).one()
            
            audit_file_demo = get_full_audit_data_for_xml(session, demo_user_from_db)
            
            self.assertEqual(audit_file_demo.Header.CompanyName, "Demo Company SA (SAF-T View)")
            self.assertTrue(len(audit_file_demo.MasterFiles.Customer) >= 1, "Demo user should have customers")
            self.assertTrue(any(c.CustomerID.startswith("DEMOCUST") for c in audit_file_demo.MasterFiles.Customer))
            for customer in audit_file_demo.MasterFiles.Customer:
                self.assertEqual(customer.owner_id, demo_user_from_db.id)
            
            self.assertTrue(len(audit_file_demo.MasterFiles.Product) >= 1)
            self.assertTrue(len(audit_file_demo.MasterFiles.Supplier) >= 1)
            self.assertTrue(audit_file_demo.MasterFiles.GeneralLedgerAccounts is not None)
            self.assertTrue(len(audit_file_demo.MasterFiles.GeneralLedgerAccounts.Account) >= 1)

    @unittest.skipIf(not XSD_FILE_PATH_FOR_ENGINE_TESTS.exists(), "XSD file not found, skipping XML validation test.")
    def test_generate_and_validate_saft_file_with_demo_user_data(self):
        with Session(test_engine_module_engine) as session:
            demo_user = session.exec(select(User).where(User.username == DEMO_USER_USERNAME)).one()
            # Demo data is populated in setUp. 
            # Ensure enough data for XSD validation, core_populate_demo_data should handle this.
            
            audit_file_instance = get_full_audit_data_for_xml(session, demo_user)
            
            xml_string, errors = generate_and_validate_saft_file(audit_file_instance, str(XSD_FILE_PATH_FOR_ENGINE_TESTS))

            self.assertIsNotNone(xml_string, f"XML string should be generated. Errors: {errors}")
            self.assertEqual(len(errors), 0, f"Validation should pass for demo user data. Errors: {errors}\nXML: {xml_string[:1000] if xml_string else ''}")
            if xml_string:
                self.assertTrue(xml_string.startswith("<?xml version=\"1.0\" encoding=\"utf-8\"?>"))
                self.assertIn("<CompanyName>Demo Company SA (SAF-T View)</CompanyName>", xml_string)
                self.assertIn("<CustomerID>DEMOCUST001</CustomerID>", xml_string) # Check one of the demo customers

    @unittest.skipIf(not XSD_FILE_PATH_FOR_ENGINE_TESTS.exists(), "XSD file not found, skipping XML validation failure test.")
    def test_generate_and_validate_saft_file_invalid_data_from_demo_context(self):
        with Session(test_engine_module_engine) as session:
            demo_user = session.exec(select(User).where(User.username == DEMO_USER_USERNAME)).one()
            
            audit_file_instance = get_full_audit_data_for_xml(session, demo_user)
            # Intentionally cause an error that XSD would catch
            audit_file_instance.Header.FiscalYear = "INVALID_YEAR_FOR_XSD" # type: ignore
        
            xml_string, errors = generate_and_validate_saft_file(audit_file_instance, str(XSD_FILE_PATH_FOR_ENGINE_TESTS))

            self.assertIsNone(xml_string, "XML string should be None when validation fails.")
            self.assertTrue(len(errors) > 0, "Error list should not be empty for invalid data.")
            # Check for a specific error message related to FiscalYear
            self.assertTrue(any("INVALID_YEAR_FOR_XSD" in error for error in errors) and \
                            any("integer" in error for error in errors),
                            f"Expected FiscalYear validation error not found in {errors}")

if __name__ == '__main__':
    unittest.main()
