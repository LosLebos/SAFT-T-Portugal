import unittest
import os
import sys
from pathlib import Path
from typing import Generator, Optional

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select, Field
from lxml import etree 

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app 
from database import get_session as original_get_session 
from models import (
    User, Customer, Supplier, Product, Account as GeneralLedgerAccountSQLModel,
    CustomerAddressStructure, AddressStructure, ProductTypeEnum, SAFPTGLAccountID, AuditFile
)
import engine as engine_module 
from core.config import DEMO_USER_USERNAME 

TEST_DB_FILE_UI = "test_ui_saft_data.db" 
TEST_DATABASE_URL_UI = f"sqlite:///{TEST_DB_FILE_UI}"
test_ui_engine = None

def override_get_session_for_ui_tests() -> Generator[Session, None, None]:
    global test_ui_engine
    if test_ui_engine is None:
        raise Exception("Test UI engine not initialized.")
    with Session(test_ui_engine) as session:
        yield session

original_xsd_path_in_ui_router = None
XSD_FILE_PATH_FOR_TESTS = PROJECT_ROOT / "SAFTPT1_04_01.xsd"

class TestUIEndpoints(unittest.TestCase):
    client: TestClient
    demo_user_id: Optional[int] = None

    @classmethod
    def setUpClass(cls):
        global test_ui_engine, original_xsd_path_in_ui_router
        
        test_ui_engine = create_engine(TEST_DATABASE_URL_UI, echo=False, connect_args={"check_same_thread": False})
        app.dependency_overrides[original_get_session] = override_get_session_for_ui_tests
        
        from routers import ui as ui_router_module
        original_xsd_path_in_ui_router = ui_router_module.XSD_FILE_PATH
        ui_router_module.XSD_FILE_PATH = XSD_FILE_PATH_FOR_TESTS

        if not XSD_FILE_PATH_FOR_TESTS.exists():
            print(f"Warning: XSD file not found at {XSD_FILE_PATH_FOR_TESTS}. Some tests might be skipped.")
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        global original_xsd_path_in_ui_router
        app.dependency_overrides.clear()
        
        from routers import ui as ui_router_module
        ui_router_module.XSD_FILE_PATH = original_xsd_path_in_ui_router

        if os.path.exists(TEST_DB_FILE_UI):
            os.remove(TEST_DB_FILE_UI)

    def setUp(self):
        SQLModel.metadata.create_all(test_ui_engine)
        with Session(test_ui_engine) as session:
            from core.demo_data import create_demo_user, populate_demo_data
            demo_user = create_demo_user(session)
            populate_demo_data(session, demo_user)
            session.refresh(demo_user)
            self.demo_user_id = demo_user.id
            self.assertIsNotNone(self.demo_user_id)

    def tearDown(self):
        SQLModel.metadata.drop_all(test_ui_engine)

    def _add_full_master_data_for_saft(self, owner_id: int, customer_id_prefix: str = "CSAFT_"):
        with Session(test_ui_engine) as session:
            cust_addr = CustomerAddressStructure(AddressDetail="1 Saft St", City="Saftville", PostalCode="SF001", Country="PT")
            cust_id_val = f"{customer_id_prefix}{owner_id}_01"
            existing_cust = session.exec(select(Customer).where(Customer.CustomerID == cust_id_val)).first()
            if not existing_cust:
                cust = Customer(CustomerID=cust_id_val, AccountID=SAFPTGLAccountID("211SAFTD"), 
                                CustomerTaxID=f"PT500SAFTD{owner_id}1", CompanyName=f"SAFT Customer for User {owner_id}", 
                                BillingAddress=cust_addr, owner_id=owner_id)
                session.add(cust)
            
            if not session.exec(select(Supplier).where(Supplier.SupplierID == "SSAGLOB01")).first():
                sup_addr = AddressStructure(AddressDetail="Global Sup St", City="Globalsup", PostalCode="GS001", Country="ES")
                sup = Supplier(SupplierID="SSAGLOB01", AccountID=SAFPTGLAccountID("221GLOB"), SupplierTaxID="ESGLOB001", CompanyName="Global SAFT Supplier", BillingAddress=sup_addr)
                session.add(sup)
            
            if not session.exec(select(Product).where(Product.ProductCode == "PSAGLOB01")).first():
                prod = Product(ProductType=ProductTypeEnum.P, ProductCode="PSAGLOB01", ProductDescription="Global SAFT Product", ProductNumberCode="PNSAGLOB01")
                session.add(prod)
            
            if not session.exec(select(GeneralLedgerAccountSQLModel).where(GeneralLedgerAccountSQLModel.AccountID == SAFPTGLAccountID("111SAGLOB"))).first():
                acc = GeneralLedgerAccountSQLModel(AccountID=SAFPTGLAccountID("111SAGLOB"), AccountDescription="Global SAFT Cash", OpeningDebitBalance=0, OpeningCreditBalance=0, ClosingDebitBalance=0, ClosingCreditBalance=0, GroupingCategory="GM")
                session.add(acc)
            session.commit()

    def test_view_customers_shows_demo_data_and_navbar(self):
        response = self.client.get("/ui/view/customers") 
        self.assertEqual(response.status_code, 200)
        self.assertIn("Customer Master Files", response.text)
        self.assertIn("DEMOCUST001", response.text) 
        self.assertIn("Gadgets & Gizmos Ltd (Demo)", response.text)
        self.assertIn("Mode: <strong>Demo</strong> (Read-only sample data)", response.text)
        self.assertNotIn("Logged in as:", response.text) # Check "Logged in as" is not present
        self.assertIn("You are currently in Demo Mode.", response.text)

    def test_view_customers_empty_if_no_demo_customer_data(self):
        with Session(test_ui_engine) as session: 
            demo_user = session.exec(select(User).where(User.username == DEMO_USER_USERNAME)).one()
            existing_customers = session.exec(select(Customer).where(Customer.owner_id == demo_user.id)).all()
            for cust in existing_customers:
                session.delete(cust)
            session.commit()

        response = self.client.get("/ui/view/customers")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No customers found for the current user context.", response.text)
        self.assertIn("Mode: <strong>Demo</strong> (Read-only sample data)", response.text)
        self.assertNotIn("Logged in as:", response.text)

    @unittest.skipIf(not XSD_FILE_PATH_FOR_TESTS.exists(), "XSD file not found, skipping SAFT generation.")
    def test_generate_saft_always_uses_demo_data_and_context(self):
        self.assertIsNotNone(self.demo_user_id)
        self._add_full_master_data_for_saft(owner_id=self.demo_user_id, customer_id_prefix="CSFDEMO_UI_")

        response = self.client.get("/ui/actions/generate-saft") 
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["media-type"], "application/xml")
        xml_content = response.content.decode('utf-8')
        self.assertIn("<CompanyName>Demo Company SA (SAF-T View)</CompanyName>", xml_content)
        self.assertIn(f"<CustomerID>CSFDEMO_UI_{self.demo_user_id}_01</CustomerID>", xml_content) 

    @unittest.skipIf(not XSD_FILE_PATH_FOR_TESTS.exists(), "XSD file not found, skipping SAFT validation failure test.")
    def test_generate_saft_validation_failure_renders_error_html_with_demo_navbar(self):
        original_get_full_audit_data = engine_module.get_full_audit_data_for_xml

        def mock_get_invalid_audit_data(db_session: Session, current_user: User) -> AuditFile: 
            self.assertEqual(current_user.username, DEMO_USER_USERNAME) 
            from models import Header, AuditFile, MasterFiles, AddressStructure, SAFPTDateSpan, TaxAccountingBasisEnum, CurrencyPT, CustomerAddressStructure as CustAddrPydantic, Customer as CustPydantic
            
            faulty_header = Header( 
                AuditFileVersion="1.04_01", CompanyID=current_user.username, TaxRegistrationNumber=999999999,
                TaxAccountingBasis=TaxAccountingBasisEnum.F, CompanyName=f"Demo Faulty Co",
                CompanyAddress=AddressStructure(AddressDetail="1 Fault St", City="Faultburg", PostalCode="0000-000", Country="PT"),
                FiscalYear="NOT_A_YEAR", 
                StartDate=SAFPTDateSpan(2023,1,1), EndDate=SAFPTDateSpan(2023,12,31),
                CurrencyCode=CurrencyPT.EUR, DateCreated=SAFPTDateSpan.today(), TaxEntity="Global",
                ProductCompanyTaxID="999999999", SoftwareCertificateNumber=9876, ProductID="FaultyGen/1.0", ProductVersion="1.0"
            )
            mf = MasterFiles(Customer=[
                CustPydantic(CustomerID="CFAULT_DEMO", AccountID=SAFPTGLAccountID("ACFAULT_DEMO"), CustomerTaxID="PTFAULT_DEMO", 
                         CompanyName="Fault Cust Demo", 
                         BillingAddress=CustAddrPydantic(AddressDetail=".",City=".",PostalCode=".",Country="PT"), 
                         SelfBillingIndicator=0, owner_id=current_user.id ) # Added owner_id here as well
            ])
            return AuditFile(Header=faulty_header, MasterFiles=mf) 

        engine_module.get_full_audit_data_for_xml = mock_get_invalid_audit_data
        
        try:
            response = self.client.get("/ui/actions/generate-saft") 
            self.assertEqual(response.status_code, 200) 
            self.assertIn("text/html", response.headers["content-type"])
            self.assertIn("An Error Occurred", response.text)
            self.assertIn("Element 'FiscalYear'", response.text) 
            self.assertIn("not a valid value of the atomic type 'xs:integer'", response.text)
            self.assertIn("Mode: <strong>Demo</strong> (Read-only sample data)", response.text)
            self.assertNotIn("Logged in as:", response.text) 
        finally:
            engine_module.get_full_audit_data_for_xml = original_get_full_audit_data

    def test_help_page_shows_demo_mode_navbar(self):
        response = self.client.get("/ui/help") 
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Help / Documentation", response.text)
        self.assertIn("Welcome to SAF-T Tools", response.text)
        self.assertIn("Mode: <strong>Demo</strong> (Read-only sample data)", response.text)
        self.assertNotIn("Logged in as:", response.text)

if __name__ == '__main__':
    unittest.main()
