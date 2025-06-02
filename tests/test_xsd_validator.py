import unittest
import os
from lxml import etree # For creating controlled invalid XML for testing if needed

# Adjust sys.path if running tests from a subfolder locally
import sys
# if not any(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) in p for p in sys.path):
#    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xsd_validator import validate_saft_xml
from xml_generator import generate_saft_xml
from models import ( # Import necessary models to construct a valid AuditFile instance
    AuditFile, Header, MasterFiles, Customer, CustomerAddressStructure, Product, ProductTypeEnum,
    GeneralLedgerEntries, Journal, Transaction, Lines, DebitLine, CreditLine,
    AddressStructure, SAFPTGLAccountID, SAFPTDateSpan, SAFPTAccountingPeriod, TransactionTypeEnum,
    SAFdateTimeType, SAFmonetaryType, AuditFileVersion, CompanyIDType, SAFPTPortugueseVatNumber,
    TaxAccountingBasisEnum, CurrencyPT, ProductIDType
)
from decimal import Decimal

# Define the path to the XSD file.
# This assumes the XSD file is in the root of the repository where tests might be run from.
# Or, if tests are run from 'tests' subdir, it's one level up.
XSD_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', "SAFTPT1_04_01.xsd")
# If the tool places all files in a flat directory, this might need to be just "SAFTPT1_04_01.xsd"
# For robustness, check if the file exists at the assumed path, or allow override via environment variable.
if not os.path.exists(XSD_FILE_PATH):
    # Fallback for flat directory structure if the above relative path doesn't work
    XSD_FILE_PATH = "SAFTPT1_04_01.xsd"


class TestXsdValidator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(XSD_FILE_PATH):
            raise unittest.SkipTest(f"XSD file not found at {XSD_FILE_PATH}, skipping XSD validation tests.")

    def _create_valid_audit_file_instance(self) -> AuditFile:
        """Helper to create a reasonably complete and valid AuditFile instance for testing."""
        header = Header(
            AuditFileVersion="1.04_01", CompanyID="501234567", TaxRegistrationNumber=501234567,
            TaxAccountingBasis=TaxAccountingBasisEnum.F, CompanyName="Valid Company Ltd",
            CompanyAddress=AddressStructure(AddressDetail="Main St 123", City="Valhalla", PostalCode="1234-567", Country="PT"),
            FiscalYear=2023, StartDate=SAFPTDateSpan(2023, 1, 1), EndDate=SAFPTDateSpan(2023, 12, 31),
            CurrencyCode=CurrencyPT.EUR, DateCreated=SAFPTDateSpan.today(), TaxEntity="Global",
            ProductCompanyTaxID="501234567", SoftwareCertificateNumber=1234, ProductID="ValidGen/1.0", ProductVersion="1.0"
        )
        customer_addr = CustomerAddressStructure(AddressDetail="Cust St 1", City="Clientburg", PostalCode="1111-111", Country="PT")
        customer = Customer(
            CustomerID="CVAL001", AccountID=SAFPTGLAccountID("211111"), CustomerTaxID="PT123123123",
            CompanyName="Valid Customer Inc", BillingAddress=customer_addr, SelfBillingIndicator=0
        )
        product = Product(
            ProductType=ProductTypeEnum.P, ProductCode="PVAL001", ProductDescription="Valid Product", ProductNumberCode="PNVAL001"
        )
        master_files = MasterFiles(Customer=[customer], Product=[product])
        
        debit_line = DebitLine(
            RecordID="DRV001", AccountID=SAFPTGLAccountID("611111"), SystemEntryDate=SAFdateTimeType.now(),
            Description="Valid Debit", DebitAmount=SAFmonetaryType(Decimal("200.00"))
        )
        credit_line = CreditLine(
            RecordID="CRV001", AccountID=SAFPTGLAccountID("711111"), SystemEntryDate=SAFdateTimeType.now(),
            Description="Valid Credit", CreditAmount=SAFmonetaryType(Decimal("200.00"))
        )
        lines = Lines(DebitLine=[debit_line], CreditLine=[credit_line])
        transaction = Transaction(
            TransactionID=f"{SAFPTDateSpan.today()} JV1 TV1", Period=SAFPTAccountingPeriod(SAFPTDateSpan.today().month),
            TransactionDate=SAFPTDateSpan.today(), SourceID="UserValid", Description="Valid Transaction",
            DocArchivalNumber="DOCVAL001", TransactionType=TransactionTypeEnum.N, GLPostingDate=SAFPTDateSpan.today(), Lines=lines
        )
        journal = Journal(JournalID="JVAL01", Description="Valid Journal", Transaction=[transaction])
        gl_entries = GeneralLedgerEntries(
            NumberOfEntries=1, TotalDebit=SAFmonetaryType(Decimal("200.00")), TotalCredit=SAFmonetaryType(Decimal("200.00")), Journal=[journal]
        )
        return AuditFile(Header=header, MasterFiles=master_files, GeneralLedgerEntries=gl_entries)

    def test_validate_saft_xml_with_valid_xml(self):
        """Test validation with a well-formed and schema-compliant XML."""
        audit_file_instance = self._create_valid_audit_file_instance()
        # Ensure all mandatory fields for XSD are populated in the instance above.
        # This includes things like SoftwareCertificateNumber, ProductCompanyTaxID etc in Header.
        
        xml_string = generate_saft_xml(audit_file_instance, pretty_print=False) # Use compact for this test
        is_valid, errors = validate_saft_xml(xml_string, XSD_FILE_PATH)
        
        # For debugging if it fails:
        if not is_valid:
            print("Validation failed for supposedly valid XML. Errors:")
            for error in errors:
                print(error)
            # print("\nGenerated XML that failed validation:\n", xml_string[:2000]) # Print first 2k chars
        
        self.assertTrue(is_valid, "Generated XML should be valid against the SAF-T XSD.")
        self.assertEqual(errors, [])

    def test_validate_saft_xml_missing_required_header_element(self):
        """Test with XML missing a required element (e.g., Header.CompanyName)."""
        audit_file_instance = self._create_valid_audit_file_instance()
        audit_file_instance.Header.CompanyName = None # CompanyName is mandatory
        
        # model_dump(exclude_none=True) will omit CompanyName.
        # The XSD requires CompanyName in Header.
        xml_string = generate_saft_xml(audit_file_instance, pretty_print=True)
        
        # For debugging: print(xml_string)
        
        is_valid, errors = validate_saft_xml(xml_string, XSD_FILE_PATH)
        self.assertFalse(is_valid, "XML should be invalid due to missing Header.CompanyName.")
        self.assertTrue(any("Element 'Header': Missing child element(s). Expected is ( CompanyName )" in error for error in errors), 
                        f"Error message not as expected. Got: {errors}")


    def test_validate_saft_xml_invalid_data_type(self):
        """Test with XML having a data type error (e.g., text in FiscalYear)."""
        # Create a structurally valid XML but with a data type mismatch.
        # Easiest way is to generate a valid one, then manipulate the string, or use xmltodict to modify dict then unparse.
        audit_file_instance = self._create_valid_audit_file_instance()
        xml_dict = xmltodict.parse(generate_saft_xml(audit_file_instance, pretty_print=False))
        
        # Introduce a data type error: FiscalYear should be an integer.
        xml_dict["AuditFile"]["Header"]["FiscalYear"] = "NotAYear" 
        
        invalid_xml_string = xmltodict.unparse(xml_dict, pretty=False)
        is_valid, errors = validate_saft_xml(invalid_xml_string, XSD_FILE_PATH)
        
        self.assertFalse(is_valid, "XML should be invalid due to incorrect data type for FiscalYear.")
        self.assertTrue(any("'NotAYear' is not a valid value for 'integer'" in error for error in errors) or \
                        any("Element 'FiscalYear': 'NotAYear' is not a valid value of the atomic type 'xs:integer'." in error for error in errors), # More specific lxml error
                        f"Error message for FiscalYear data type not as expected. Got: {errors}")


    def test_validate_saft_xml_non_existent_xsd_file(self):
        """Test validation attempt with a non-existent XSD file path."""
        valid_xml_string = "<AuditFile><Header><Test>T</Test></Header></AuditFile>" # Minimal valid structure (not schema valid)
        is_valid, errors = validate_saft_xml(valid_xml_string, "non_existent_schema.xsd")
        self.assertFalse(is_valid)
        self.assertTrue(any("non_existent_schema.xsd" in error and ("No such file" in error or "not found" in error) for error in errors))


    def test_validate_saft_xml_malformed_xml(self):
        """Test validation with a malformed XML string."""
        malformed_xml_string = "<AuditFile><Header><CompanyName>Test Co</CompanyName>" # Missing </Header> and </AuditFile>
        is_valid, errors = validate_saft_xml(malformed_xml_string, XSD_FILE_PATH)
        self.assertFalse(is_valid)
        self.assertTrue(any("Malformed XML" in error for error in errors) or \
                        any("Premature end of document" in error for error in errors) or \
                        any("Unclosed tag" in error for error in errors), # Varies by parser detail
                        f"Error message for malformed XML not as expected. Got: {errors}")

    def test_validate_saft_xml_empty_string(self):
        """Test validation with an empty XML string."""
        is_valid, errors = validate_saft_xml("", XSD_FILE_PATH)
        self.assertFalse(is_valid)
        self.assertTrue(any("XML document loaded from string is empty" in error or "Start tag expected" in error for error in errors),
                        f"Error message for empty XML string not as expected. Got: {errors}")

if __name__ == '__main__':
    # Adjust path for local execution if necessary
    if not os.path.exists(XSD_FILE_PATH) and XSD_FILE_PATH == "../SAFTPT1_04_01.xsd":
        # Try flat path if relative one failed (e.g. when tool runs it flat)
        XSD_FILE_PATH = "SAFTPT1_04_01.xsd"
        
    # Add project root to sys.path to allow finding other modules if running this test file directly
    # from the 'tests' subdirectory. This is mainly for local development convenience.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    unittest.main()
