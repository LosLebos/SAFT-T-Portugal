import unittest
import xmltodict # For parsing generated XML back to dict for easier assertions
from decimal import Decimal

# Assuming xml_generator.py and models.py are accessible.
# Adjust sys.path if running tests from a subfolder locally and they are not in the root.
# For the tool environment, files are usually co-located or paths handled.
import sys
import os
# if not any(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) in p for p in sys.path):
#     sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xml_generator import generate_saft_xml, SAFT_PT_NAMESPACE
from models import (
    AuditFile, Header, MasterFiles, Customer, CustomerAddressStructure, Product, ProductTypeEnum,
    GeneralLedgerEntries, Journal, Transaction, Lines, DebitLine, CreditLine,
    AddressStructure, SAFPTGLAccountID, SAFPTDateSpan, SAFPTAccountingPeriod, TransactionTypeEnum,
    SAFdateTimeType, SAFmonetaryType, AuditFileVersion, CompanyIDType, SAFPTPortugueseVatNumber,
    TaxAccountingBasisEnum, CurrencyPT, ProductIDType
)

class TestXmlGenerator(unittest.TestCase):

    def _create_sample_audit_file_instance(self) -> AuditFile:
        """Helper method to create a populated AuditFile instance for testing."""
        header = Header(
            AuditFileVersion="1.04_01",
            CompanyID="123456789", # Using a simple string for CompanyIDType for test
            TaxRegistrationNumber=123456789,
            TaxAccountingBasis=TaxAccountingBasisEnum.F,
            CompanyName="Test Company XML",
            CompanyAddress=AddressStructure(
                AddressDetail="Main Street 1", City="Test City", PostalCode="1234-567", Country="PT"
            ),
            FiscalYear=2023,
            StartDate=SAFPTDateSpan(2023, 1, 1),
            EndDate=SAFPTDateSpan(2023, 12, 31),
            CurrencyCode=CurrencyPT.EUR,
            DateCreated=SAFPTDateSpan(2023, 11, 15),
            TaxEntity="Global",
            ProductCompanyTaxID="123456789",
            SoftwareCertificateNumber=1234,
            ProductID="TestGen/1.0",
            ProductVersion="1.0"
        )

        customer_addr = CustomerAddressStructure(AddressDetail="Side Ave 10", City="Clientville", PostalCode="7654-321", Country="PT")
        customer = Customer(
            CustomerID="CXML001", AccountID=SAFPTGLAccountID("211001"), CustomerTaxID="PT509999999",
            CompanyName="XML Client Omega", BillingAddress=customer_addr, SelfBillingIndicator=0
        )
        
        product = Product(
            ProductType=ProductTypeEnum.P, ProductCode="PXML001",
            ProductDescription="XML Test Product", ProductNumberCode="XMLPN001"
        )
        
        master_files = MasterFiles(Customer=[customer], Product=[product])

        debit_line = DebitLine(
            RecordID="DR001", AccountID=SAFPTGLAccountID("610001"), SystemEntryDate=SAFdateTimeType(2023,11,15,10,0,0),
            Description="Sale related debit", DebitAmount=SAFmonetaryType(Decimal("123.45"))
        )
        credit_line = CreditLine(
            RecordID="CR001", AccountID=SAFPTGLAccountID("710001"), SystemEntryDate=SAFdateTimeType(2023,11,15,10,0,0),
            Description="Sale related credit", CreditAmount=SAFmonetaryType(Decimal("123.45"))
        )
        lines = Lines(DebitLine=[debit_line], CreditLine=[credit_line])
        
        transaction = Transaction(
            TransactionID="2023-11-15 J1 T1", Period=SAFPTAccountingPeriod(11), TransactionDate=SAFPTDateSpan(2023,11,15),
            SourceID="UserTest", Description="XML Test Transaction", DocArchivalNumber="XMLDOC001",
            TransactionType=TransactionTypeEnum.N, GLPostingDate=SAFPTDateSpan(2023,11,15), Lines=lines
        )
        
        journal = Journal(JournalID="JXML01", Description="XML Test Journal", Transaction=[transaction])
        
        gl_entries = GeneralLedgerEntries(
            NumberOfEntries=1, TotalDebit=SAFmonetaryType(Decimal("123.45")), TotalCredit=SAFmonetaryType(Decimal("123.45")),
            Journal=[journal]
        )

        return AuditFile(Header=header, MasterFiles=master_files, GeneralLedgerEntries=gl_entries)

    def test_generate_saft_xml_basic_structure_and_content_pretty(self):
        """Test XML generation with pretty_print=True for basic structure and content."""
        audit_file_instance = self._create_sample_audit_file_instance()
        xml_output = generate_saft_xml(audit_file_instance, pretty_print=True)

        self.assertTrue(xml_output.startswith("<?xml version=\"1.0\" encoding=\"utf-8\"?>"))
        self.assertIn("\n", xml_output) # Check for newlines, indicating pretty printing

        # Parse back to dictionary to verify structure
        try:
            parsed_dict = xmltodict.parse(xml_output)
        except Exception as e:
            self.fail(f"Generated XML (pretty) is not well-formed: {e}\nXML:\n{xml_output}")

        self.assertIn("AuditFile", parsed_dict)
        audit_file_dict_content = parsed_dict["AuditFile"]
        
        self.assertEqual(audit_file_dict_content["@xmlns"], SAFT_PT_NAMESPACE)

        # Check for key sections
        self.assertIn("Header", audit_file_dict_content)
        self.assertIn("MasterFiles", audit_file_dict_content)
        self.assertIn("GeneralLedgerEntries", audit_file_dict_content)

        # Check some specific values (examples)
        self.assertEqual(audit_file_dict_content["Header"]["CompanyName"], "Test Company XML")
        self.assertEqual(audit_file_dict_content["MasterFiles"]["Customer"]["CustomerID"], "CXML001")
        self.assertEqual(audit_file_dict_content["MasterFiles"]["Product"]["ProductCode"], "PXML001")
        self.assertEqual(audit_file_dict_content["GeneralLedgerEntries"]["Journal"]["Transaction"]["Description"], "XML Test Transaction")
        self.assertEqual(audit_file_dict_content["GeneralLedgerEntries"]["Journal"]["Transaction"]["Lines"]["DebitLine"]["DebitAmount"], "123.45") # xmltodict converts Decimal to string

    def test_generate_saft_xml_compact_output(self):
        """Test XML generation with pretty_print=False for compact output."""
        audit_file_instance = self._create_sample_audit_file_instance()
        xml_output = generate_saft_xml(audit_file_instance, pretty_print=False)

        self.assertTrue(xml_output.startswith("<?xml version=\"1.0\" encoding=\"utf-8\"?>"))
        # A very basic check for no newlines between tags, though this can be tricky.
        # A more robust check would be to compare length or parse and re-unparse without pretty.
        self.assertNotIn("\n<Header>", xml_output) # Example check for compactness

        try:
            parsed_dict = xmltodict.parse(xml_output) # Should still be valid XML
        except Exception as e:
            self.fail(f"Generated XML (compact) is not well-formed: {e}\nXML:\n{xml_output}")

        self.assertIn("AuditFile", parsed_dict)
        self.assertEqual(parsed_dict["AuditFile"]["Header"]["CompanyName"], "Test Company XML")


    def test_generate_saft_xml_type_error_for_invalid_input(self):
        """Test that a TypeError is raised for invalid input type."""
        with self.assertRaises(TypeError):
            generate_saft_xml("not_an_auditfile_instance")

    def test_xml_decimal_and_date_formatting(self):
        """Test specific formatting of decimal and date types."""
        audit_file_instance = self._create_sample_audit_file_instance()
        xml_output = generate_saft_xml(audit_file_instance)
        parsed_dict = xmltodict.parse(xml_output)
        
        # Dates should be YYYY-MM-DD
        self.assertEqual(parsed_dict["AuditFile"]["Header"]["StartDate"], "2023-01-01")
        # Datetimes should be ISO format (Pydantic default usually includes T)
        # SAFdateTimeType is just datetime, so default Pydantic serialization to string for JSON is ISO
        # xmltodict will just use that string.
        # Example: '2023-11-15T10:00:00' if it were a direct field.
        # Here SystemEntryDate is inside DebitLine
        self.assertTrue("T" in parsed_dict["AuditFile"]["GeneralLedgerEntries"]["Journal"]["Transaction"]["Lines"]["DebitLine"]["SystemEntryDate"])
        
        # Decimals are converted to strings by xmltodict by default
        self.assertEqual(parsed_dict["AuditFile"]["GeneralLedgerEntries"]["TotalDebit"], "123.45")
        self.assertEqual(parsed_dict["AuditFile"]["GeneralLedgerEntries"]["Journal"]["Transaction"]["Lines"]["DebitLine"]["DebitAmount"], "123.45")

    # More tests could be added for:
    # - Missing optional fields in the AuditFile instance (ensure exclude_none=True works)
    # - Special characters in string fields (though xmltodict should handle escaping)
    # - Correct handling of lists (e.g., multiple Customers, Products, Journals, Transactions, Lines)

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    # Ensure that the script can find 'xml_generator.py' and 'models.py'
    # If they are in the parent directory:
    if not any(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) in p for p in sys.path):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    unittest.main()
