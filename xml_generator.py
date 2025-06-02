import xmltodict
from typing import Dict, Any
import logging

# Assuming models.py is accessible in the same environment/path
from models import AuditFile # The main Pydantic model for the entire SAF-T file

logger = logging.getLogger(__name__)

# Default SAF-T PT Namespace
SAFT_PT_NAMESPACE = "urn:OECD:StandardAuditFile-Tax:PT_1.04_01"

def generate_saft_xml(audit_file_data: AuditFile, pretty_print: bool = True) -> str:
    """
    Generates a SAF-T XML string from an AuditFile Pydantic model instance.

    Args:
        audit_file_data: An instance of the AuditFile Pydantic model.
        pretty_print: If True, the output XML will be pretty-printed (indented).

    Returns:
        A string containing the SAF-T XML.
    """
    if not isinstance(audit_file_data, AuditFile):
        raise TypeError("Input must be an instance of the AuditFile Pydantic model.")

    logger.info(f"Generating SAF-T XML for AuditFile version: {audit_file_data.Header.AuditFileVersion if audit_file_data.Header else 'Unknown'}")

    try:
        # Convert the Pydantic model to a dictionary.
        # exclude_none=True is important to omit fields that are not set.
        # by_alias=True is used if Pydantic models have field aliases for XML tag names.
        # For SAF-T, tag names often match model field names directly if models were generated from XSD carefully.
        # However, if aliases like 'InvoiceNo' for 'invoice_no' are used, by_alias=True is critical.
        # Based on current models.py, aliases are not heavily used, field names match tags.
        # Let's assume by_alias=False for now, or ensure models.py uses aliases if needed.
        # Forcing by_alias=True is safer if there's any doubt.
        # After reviewing models.py, most fields are direct matches (e.g. CustomerID).
        # Using by_alias=True is a good default.
        
        # For fields that are Enums or custom types, Pydantic's dump should convert them to their primitive values.
        # Example: SAFPTDateSpan (date) should become "YYYY-MM-DD" string.
        #          TaxAccountingBasisEnum (Literal) should become its string value.
        #          SAFmonetaryType (Decimal) should become float or string compatible with XML.
        # Pydantic's model_dump handles this serialization to JSON-compatible types well.
        # xmltodict then takes these Python primitives.
        
        # It's crucial that date/datetime/decimal fields are converted to strings
        # in the format expected by the XSD *before* xmltodict processing if Pydantic doesn't do it by default.
        # Pydantic's model_dump(mode='json') would typically do this.
        # Let's use model_dump(mode='python', by_alias=True, exclude_none=True) and assume primitives are fine.
        # If specific string formatting is needed for date/decimal, custom serializers in Pydantic models are the way.
        # For now, we rely on default Pydantic serialization and xmltodict's handling of primitives.

        audit_file_dict = audit_file_data.model_dump(by_alias=True, exclude_none=True)
        
        # The root element of the SAF-T XML is "AuditFile".
        # xmltodict.unparse expects a dictionary where the top-level key is the root element name.
        # We also need to add the namespace to the root element.
        xml_dict_with_root = {
            "AuditFile": {
                "@xmlns": SAFT_PT_NAMESPACE,
                **audit_file_dict
            }
        }
        
        # Unparse the dictionary to an XML string.
        # `full_document=True` ensures that an XML declaration is included.
        xml_string = xmltodict.unparse(xml_dict_with_root, pretty=pretty_print, full_document=True, encoding='utf-8')
        
        logger.info("SAF-T XML string generated successfully.")
        return xml_string

    except Exception as e:
        logger.error(f"Error during XML generation: {e}", exc_info=True)
        raise ValueError(f"Failed to generate XML: {e}")


if __name__ == '__main__':
    # This is an example of how to use the generator.
    # It requires constructing a valid AuditFile instance.
    # For testing, see tests/test_xml_generator.py
    
    print("Example usage of xml_generator.py (constructs a minimal AuditFile instance):")

    # Import necessary sub-models for the example
    from models import (Header, MasterFiles, Customer, CustomerAddressStructure, SAFPTGLAccountID,
                        Product, ProductTypeEnum, GeneralLedgerEntries, Journal, Transaction, Lines,
                        DebitLine, CreditLine, SAFPTDateSpan, SAFPTAccountingPeriod, TransactionTypeEnum,
                        SAFdateTimeType, SAFmonetaryType, AddressStructure, AuditFileVersion, CompanyIDType,
                        SAFPTPortugueseVatNumber, TaxAccountingBasisEnum, CurrencyPT, ProductIDType)
    from decimal import Decimal

    try:
        # 1. Create Header
        header_instance = Header(
            AuditFileVersion="1.04_01",
            CompanyID="501234567", # NIF if no commercial registry
            TaxRegistrationNumber=501234567,
            TaxAccountingBasis=TaxAccountingBasisEnum.F, # Faturacao
            CompanyName="Test Company SA",
            CompanyAddress=AddressStructure(
                AddressDetail="Rua Teste 123", City="Lisboa", PostalCode="1000-001", Country="PT"
            ),
            FiscalYear=SAFPTDateSpan.today().year,
            StartDate=SAFPTDateSpan(SAFPTDateSpan.today().year, 1, 1),
            EndDate=SAFPTDateSpan(SAFPTDateSpan.today().year, 12, 31),
            CurrencyCode=CurrencyPT.EUR,
            DateCreated=SAFPTDateSpan.today(),
            TaxEntity="Global",
            ProductCompanyTaxID="501234567",
            SoftwareCertificateNumber=0, # Actual number required
            ProductID="TestSAFTPTGenerator/1.0",
            ProductVersion="1.0"
        )

        # 2. Create MasterFiles
        customer_address = CustomerAddressStructure(
            AddressDetail="Av. Liberdade 100", City="Lisboa", PostalCode="1250-145", Country="PT"
        )
        customer_instance = Customer(
            id=None, # SQLModel ID, not part of XML structure directly unless also an XML field
            CustomerID="C001",
            AccountID=SAFPTGLAccountID("21110001"),
            CustomerTaxID="PT999888777",
            CompanyName="Cliente Exemplo LDA",
            BillingAddress=customer_address,
            SelfBillingIndicator=0
        )
        product_instance = Product(
            id=None,
            ProductType=ProductTypeEnum.P,
            ProductCode="PROD001",
            ProductDescription="Produto Teste",
            ProductNumberCode="PN001"
        )
        master_files_instance = MasterFiles(
            Customer=[customer_instance],
            Product=[product_instance]
            # GeneralLedgerAccounts and Supplier omitted for this minimal example
        )

        # 3. Create GeneralLedgerEntries (minimal)
        debit_line = DebitLine(
            RecordID="DR1", AccountID=SAFPTGLAccountID("61110001"), SystemEntryDate=SAFdateTimeType.now(),
            Description="Debit example", DebitAmount=SAFmonetaryType(Decimal("100.00"))
        )
        credit_line = CreditLine(
            RecordID="CR1", AccountID=SAFPTGLAccountID("71110001"), SystemEntryDate=SAFdateTimeType.now(),
            Description="Credit example", CreditAmount=SAFmonetaryType(Decimal("100.00"))
        )
        lines_instance = Lines(DebitLine=[debit_line], CreditLine=[credit_line])
        
        transaction_instance = Transaction(
            TransactionID=f"{SAFPTDateSpan.today()} Journal1 Entry1", # Needs specific format
            Period=SAFPTAccountingPeriod(SAFPTDateSpan.today().month),
            TransactionDate=SAFPTDateSpan.today(),
            SourceID="UserXYZ",
            Description="Daily Sales Summary",
            DocArchivalNumber="DOC001",
            TransactionType=TransactionTypeEnum.N,
            GLPostingDate=SAFPTDateSpan.today(),
            Lines=lines_instance
        )
        journal_instance = Journal(
            JournalID="JOURNAL01", Description="Sales Journal", Transaction=[transaction_instance]
        )
        gl_entries_instance = GeneralLedgerEntries(
            NumberOfEntries=1, TotalDebit=SAFmonetaryType(Decimal("100.00")), TotalCredit=SAFmonetaryType(Decimal("100.00")),
            Journal=[journal_instance]
        )

        # 4. Create AuditFile
        audit_file_instance = AuditFile(
            Header=header_instance,
            MasterFiles=master_files_instance,
            GeneralLedgerEntries=gl_entries_instance
            # SourceDocuments omitted for this minimal example
        )

        # 5. Generate XML
        xml_output_pretty = generate_saft_xml(audit_file_instance, pretty_print=True)
        print("\n--- Pretty XML Output ---")
        print(xml_output_pretty)

        xml_output_compact = generate_saft_xml(audit_file_instance, pretty_print=False)
        print("\n--- Compact XML Output ---")
        # print(xml_output_compact) # Usually too long for console, but good for checking it runs

        # Save to file for inspection
        with open("example_saft.xml", "w", encoding="utf-8") as f:
            f.write(xml_output_pretty)
        print("\nSaved pretty XML to example_saft.xml")

    except Exception as e:
        print(f"Error in XML generation example: {e}")
        logger.error("Error in XML generator example usage", exc_info=True)
