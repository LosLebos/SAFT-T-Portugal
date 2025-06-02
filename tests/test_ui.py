import unittest
import os
import sys
from pathlib import Path
from typing import Generator, Dict, Type, List

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, Field
from lxml import etree # For parsing XML content in tests
import xmltodict # For comparing XML structure if needed

# --- Add project root to sys.path to allow importing app modules ---
# This assumes 'tests' is a subdirectory of the project root where main.py, models.py etc. reside.
# Adjust if your structure is different or the tool handles paths.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now import application modules
from main import app # The FastAPI application instance
from database import get_session as original_get_session # To override
from models import (
    Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel,
    CustomerAddressStructure, AddressStructure, ProductTypeEnum, SAFPTGLAccountID,
    AuditFile # For type hinting if checking engine output
)
# Import engine to potentially mock get_full_audit_data_for_xml for specific error tests
import engine as engine_module 

# --- Test Database Setup ---
TEST_DB_FILE_UI = "test_ui_saft_data.db" # Separate DB for UI tests
TEST_DATABASE_URL_UI = f"sqlite:///{TEST_DB_FILE_UI}"
test_ui_engine = None

def override_get_session_for_ui_tests() -> Generator[Session, None, None]:
    global test_ui_engine
    if test_ui_engine is None:
        raise Exception("Test UI engine not initialized.")
    with Session(test_ui_engine) as session:
        yield session
        # Let tests manage their own commits or rely on endpoint logic's commits.

# Store original XSD path from ui router to restore later if patched
original_xsd_path_in_ui_router = None
XSD_FILE_PATH_FOR_TESTS = PROJECT_ROOT / "SAFTPT1_04_01.xsd"


class TestUIEndpoints(unittest.TestCase):

    client: TestClient

    @classmethod
    def setUpClass(cls):
        global test_ui_engine, original_xsd_path_in_ui_router
        
        test_ui_engine = create_engine(TEST_DATABASE_URL_UI, echo=False, connect_args={"check_same_thread": False})
        
        # Patch the get_session dependency for the FastAPI app
        app.dependency_overrides[original_get_session] = override_get_session_for_ui_tests
        
        # Patch XSD path in ui.py router if it's different from what tests expect
        # This ensures tests use a known XSD path.
        from routers import ui as ui_router_module
        original_xsd_path_in_ui_router = ui_router_module.XSD_FILE_PATH
        ui_router_module.XSD_FILE_PATH = XSD_FILE_PATH_FOR_TESTS

        # Ensure XSD exists for tests that need it, otherwise skip them in the test methods
        if not XSD_FILE_PATH_FOR_TESTS.exists():
            print(f"Warning: XSD file not found at {XSD_FILE_PATH_FOR_TESTS}. Some tests might be skipped or fail if they rely on XSD validation.")

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        global original_xsd_path_in_ui_router
        # Restore original get_session (important if other test classes use the app)
        app.dependency_overrides.clear()
        
        from routers import ui as ui_router_module
        ui_router_module.XSD_FILE_PATH = original_xsd_path_in_ui_router

        if os.path.exists(TEST_DB_FILE_UI):
            os.remove(TEST_DB_FILE_UI)

    def setUp(self):
        """Create tables before each test."""
        SQLModel.metadata.create_all(test_ui_engine)

    def tearDown(self):
        """Drop tables after each test."""
        SQLModel.metadata.drop_all(test_ui_engine)

    def _ensure_user_exists_and_get_headers(self, username="testuiuser", password="TestUIPassword123!") -> Dict[str, str]:
        """Registers a user if they don't exist, then logs them in and returns auth headers."""
        with Session(test_ui_engine) as session:
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                reg_response = self.client.post("/auth/register", json={"username": username, "password": password, "email": f"{username}@example.com"})
                self.assertTrue(reg_response.status_code == 200 or reg_response.status_code == 400, f"Registration failed or user already exists: {reg_response.text}")
                # If 400 and user already registered, that's fine for this helper's purpose.
        
        login_response = self.client.post("/auth/token", data={"username": username, "password": password})
        self.assertEqual(login_response.status_code, 200, f"Failed to login user {username}: {login_response.text}")
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _get_user_id(self, username: str) -> Optional[int]:
        with Session(test_ui_engine) as session:
            user = session.exec(select(User).where(User.username == username)).first()
            return user.id if user else None

    def _add_sample_customer_to_db(self, owner_id: int, customer_id="CUI001", company_name="UI Test Customer"):
        with Session(test_ui_engine) as session:
            addr = CustomerAddressStructure(AddressDetail="1 UI St", City="UITown", PostalCode="UI123", Country="PT")
            customer = Customer(
                CustomerID=customer_id, AccountID=SAFPTGLAccountID("211ACC"), CustomerTaxID=f"PT999{customer_id[3:]}999",
                CompanyName=company_name, BillingAddress=addr, SelfBillingIndicator=0, owner_id=owner_id
            )
            session.add(customer)
            session.commit()
            return customer
            
    def _add_full_master_data_for_saft(self, owner_id: int):
        with Session(test_ui_engine) as session:
            cust_addr = CustomerAddressStructure(AddressDetail="1 Saft St", City="Saftville", PostalCode="SF001", Country="PT")
            cust = Customer(CustomerID="CSAFT01", AccountID=SAFPTGLAccountID("211SAFT"), CustomerTaxID="PT500SAFT01", CompanyName="SAFT Customer", BillingAddress=cust_addr, owner_id=owner_id)
            session.add(cust)
            
            # Global data (Supplier, Product, Account) - add only if they don't exist to avoid unique constraint issues across tests
            if not session.exec(select(Supplier).where(Supplier.SupplierID == "SSAFT01")).first():
                sup_addr = AddressStructure(AddressDetail="2 Saft Sup St", City="Saftsupply", PostalCode="SF002", Country="ES")
                sup = Supplier(SupplierID="SSAFT01", AccountID=SAFPTGLAccountID("221SAFT"), SupplierTaxID="ESB1234SAFT", CompanyName="SAFT Supplier Global", BillingAddress=sup_addr)
                session.add(sup)
            
            if not session.exec(select(Product).where(Product.ProductCode == "PSAFT01")).first():
                prod = Product(ProductType=ProductTypeEnum.P, ProductCode="PSAFT01", ProductDescription="SAFT Product Global", ProductNumberCode="PNSAFT01")
                session.add(prod)
            
            if not session.exec(select(GeneralLedgerAccountSQLModel).where(GeneralLedgerAccountSQLModel.AccountID == SAFPTGLAccountID("111SAFT"))).first():
                acc = GeneralLedgerAccountSQLModel(AccountID=SAFPTGLAccountID("111SAFT"), AccountDescription="SAFT Cash Global", OpeningDebitBalance=0, OpeningCreditBalance=0, ClosingDebitBalance=0, ClosingCreditBalance=0, GroupingCategory="GM")
                session.add(acc)
            session.commit()

    # --- Test Scenarios ---

    def test_view_customers_no_token_falls_to_demo_mode(self):
        # Ensure demo user and their data are populated by startup event (which uses the patched DB engine)
        # For tests, it's cleaner to explicitly call demo data population for the test session.
        with Session(test_ui_engine) as session:
            from core.demo_data import create_demo_user, populate_demo_data
            demo_user = create_demo_user(session) # Ensures demo user exists
            populate_demo_data(session, demo_user) # Populates demo data
            demo_user_id = demo_user.id

        response = self.client.get("/ui/view/customers") # No auth headers
        self.assertEqual(response.status_code, 200)
        self.assertIn("Customer Master Files", response.text)
        # Verify it shows demo user's customers
        self.assertIn("DEMOCUST001", response.text) 
        self.assertIn("Gadgets & Gizmos Ltd (Demo)", response.text)
        self.assertNotIn("Actual User Corp", response.text) # Check that other user's data isn't shown

    def test_view_customers_with_actual_user_token(self):
        actual_username = "actual_test_user"
        auth_headers = self._ensure_user_exists_and_get_headers(username=actual_username)
        actual_user_id = self._get_user_id(actual_username)
        self.assertIsNotNone(actual_user_id)

        # Add data for the actual user
        self._add_sample_customer_to_db(owner_id=actual_user_id, customer_id="ACTUALC001", company_name="Actual User Corp")
        
        # Add some demo data as well to ensure filtering works
        with Session(test_ui_engine) as session:
            from core.demo_data import create_demo_user, populate_demo_data
            demo_user = create_demo_user(session)
            populate_demo_data(session, demo_user)

        response = self.client.get("/ui/view/customers", headers=auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Actual User Corp", response.text)
        self.assertNotIn("Gadgets & Gizmos Ltd (Demo)", response.text) # Demo data should not be visible
        # Check navbar for actual user
        self.assertIn(f"Logged in as: <strong>{actual_username}</strong>", response.text)
        self.assertNotIn("Mode: <strong>Demo</strong>", response.text)


    @unittest.skipIf(not XSD_FILE_PATH_FOR_TESTS.exists(), "XSD file not found, skipping SAFT generation (demo user).")
    def test_generate_saft_no_token_demo_mode(self):
        with Session(test_ui_engine) as session: # Populate demo data
            from core.demo_data import create_demo_user, populate_demo_data
            demo_user = create_demo_user(session)
            populate_demo_data(session, demo_user)

        response = self.client.get("/ui/actions/generate-saft") # No auth headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["media-type"], "application/xml")
        xml_content = response.content.decode('utf-8')
        self.assertIn("<CompanyName>Demo Company SA (SAF-T View)</CompanyName>", xml_content)
        self.assertIn("<CustomerID>DEMOCUST001</CustomerID>", xml_content) # Check for demo customer data


    @unittest.skipIf(not XSD_FILE_PATH_FOR_TESTS.exists(), "XSD file not found, skipping SAFT generation (actual user).")
    def test_generate_saft_with_actual_user_token(self):
        actual_username = "actual_saft_user"
        auth_headers = self._ensure_user_exists_and_get_headers(username=actual_username)
        actual_user_id = self._get_user_id(actual_username)
        self.assertIsNotNone(actual_user_id)

        self._add_full_master_data_for_saft(owner_id=actual_user_id) # Add data for this specific user
        
        # Also add demo data to ensure it's not picked up
        with Session(test_ui_engine) as session:
            from core.demo_data import create_demo_user, populate_demo_data
            demo_user = create_demo_user(session)
            populate_demo_data(session, demo_user)

        response = self.client.get("/ui/actions/generate-saft", headers=auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["media-type"], "application/xml")
        xml_content = response.content.decode('utf-8')
        self.assertIn(f"<CompanyName>{actual_username}'s Company</CompanyName>", xml_content)
        self.assertIn("<CustomerID>CSAFT01</CustomerID>", xml_content) # Data added by _add_full_master_data_for_saft
        self.assertNotIn("<CompanyName>Demo Company SA (SAF-T View)</CompanyName>", xml_content)
        self.assertNotIn("<CustomerID>DEMOCUST001</CustomerID>", xml_content)


    @unittest.skipIf(not XSD_FILE_PATH_FOR_TESTS.exists(), "XSD file not found, skipping SAFT validation failure test (authenticated).")
    def test_generate_saft_validation_failure_authenticated_renders_error_html_with_navbar(self):
        auth_username = "saftfailuser_authnav"
        auth_headers = self._ensure_user_exists_and_get_headers(username=auth_username)
        original_get_full_audit_data = engine_module.get_full_audit_data_for_xml

        def mock_get_invalid_audit_data(db_session: Session, current_user: User) -> AuditFile: 
            from models import Header, AuditFile, MasterFiles, AddressStructure, SAFPTDateSpan, TaxAccountingBasisEnum, CurrencyPT, CustomerAddressStructure, Customer
            
            faulty_header = Header( 
                AuditFileVersion="1.04_01", CompanyID=current_user.username, TaxRegistrationNumber=999999999,
                TaxAccountingBasis=TaxAccountingBasisEnum.F, CompanyName=f"{current_user.username} Faulty Co",
                CompanyAddress=AddressStructure(AddressDetail="1 Fault St", City="Faultburg", PostalCode="0000-000", Country="PT"),
                FiscalYear="NOT_A_YEAR", 
                StartDate=SAFPTDateSpan(2023,1,1), EndDate=SAFPTDateSpan(2023,12,31),
                CurrencyCode=CurrencyPT.EUR, DateCreated=SAFPTDateSpan.today(), TaxEntity="Global",
                ProductCompanyTaxID="999999999", SoftwareCertificateNumber=9876, ProductID="FaultyGen/1.0", ProductVersion="1.0"
            )
            mf = MasterFiles(Customer=[
                Customer(CustomerID="CFAULT", AccountID="ACFAULT", CustomerTaxID="PTFAULT0000", CompanyName="Fault Cust", 
                         BillingAddress=CustomerAddressStructure(AddressDetail=".",City=".",PostalCode=".",Country="PT"), owner_id=current_user.id)
            ])
            return AuditFile(Header=faulty_header, MasterFiles=mf) 

        engine_module.get_full_audit_data_for_xml = mock_get_invalid_audit_data
        
        try:
            response = self.client.get("/ui/actions/generate-saft", headers=auth_headers)
            self.assertEqual(response.status_code, 200) 
            self.assertIn("text/html", response.headers["content-type"])
            self.assertIn("An Error Occurred", response.text)
            self.assertIn("Element 'FiscalYear'", response.text) 
            self.assertIn("not a valid value of the atomic type 'xs:integer'", response.text)
            # Check for navbar with correct user status
            self.assertIn(f"Logged in as: <strong>{auth_username}</strong>", response.text)
            self.assertNotIn("Mode: <strong>Demo</strong>", response.text)
        finally:
            engine_module.get_full_audit_data_for_xml = original_get_full_audit_data

    # --- Tests for new /ui/help endpoint ---
    def test_help_page_no_token_demo_mode(self):
        response = self.client.get("/ui/help") # No auth headers
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Help / Documentation", response.text)
        self.assertIn("Welcome to SAF-T Tools", response.text)
        # Check navbar for demo mode
        self.assertIn("Mode: <strong>Demo</strong>", response.text)
        self.assertNotIn("Logged in as:", response.text)

    def test_help_page_with_actual_user_token(self):
        actual_username = "help_user"
        auth_headers = self._ensure_user_exists_and_get_headers(username=actual_username)
        
        response = self.client.get("/ui/help", headers=auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Help / Documentation", response.text)
        # Check navbar for actual user
        self.assertIn(f"Logged in as: <strong>{actual_username}</strong>", response.text)
        self.assertNotIn("Mode: <strong>Demo</strong>", response.text)


if __name__ == '__main__':
    unittest.main()
