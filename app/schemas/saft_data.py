from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator, EmailStr, model_validator # Added model_validator
from datetime import date, datetime
from enum import Enum

# Placeholder for more specific SAF-T types if needed later
SAFPTDateSpan = date
SAFPTDateTime = datetime # For SAFdateTimeType
SAFMonetaryType = float
SAFDecimalType = float
SAFPTPortugueseVatNumber = int # Field(ge=100000000, le=999999999) will be used in model
SAFPTGLAccountID = str
SAFPTTransactionID = str
SAFPTJournalID = str
SAFPTProductID = str # Field(pattern=r"^[^/]+/[^/]+$") will be used in model

class AddressStructure(BaseModel):
    BuildingNumber: Optional[str] = Field(None, max_length=10)
    StreetName: Optional[str] = Field(None, max_length=200)
    AddressDetail: str = Field(..., max_length=210)
    City: str = Field(..., max_length=50)
    PostalCode: str = Field(..., max_length=20) # Add pattern validator if PT specific
    Region: Optional[str] = Field(None, max_length=50)
    Country: str = Field(..., min_length=2, max_length=2) # ISO 3166-1 alpha-2

class CustomerAddressStructure(AddressStructure):
    Country: str = Field(..., pattern=r"^([A-Z]{2}|Desconhecido)$", description="ISO 3166-1 alpha-2 country code or 'Desconhecido'.")
    # Overrides Country from AddressStructure with a new pattern

# Define Enums
class TaxAccountingBasisEnum(str, Enum):
    CONTABILIDADE = "C"
    FATURACAO_TERCEIROS = "E"
    FATURACAO = "F"
    INTEGRADA = "I"
    PARCIAL = "P"
    RECIBOS = "R" # (a)
    AUTOFATURACAO = "S"
    DOCUMENTOS_TRANSPORTE = "T" # (a)

class CurrencyCodeEnum(str, Enum):
    EUR = "EUR"

class Header(BaseModel):
    AuditFileVersion: str = Field(..., pattern=r"^1\.04_01$")
    CompanyID: str = Field(..., min_length=1, max_length=50)
    TaxRegistrationNumber: int = Field(..., ge=100000000, le=999999999) # SAFPTPortugueseVatNumber
    TaxAccountingBasis: TaxAccountingBasisEnum
    CompanyName: str = Field(..., min_length=1, max_length=100)
    BusinessName: Optional[str] = Field(None, min_length=1, max_length=60)
    CompanyAddress: AddressStructure
    FiscalYear: int = Field(..., ge=2000, le=9999)
    StartDate: SAFPTDateSpan
    EndDate: SAFPTDateSpan
    CurrencyCode: CurrencyCodeEnum
    DateCreated: SAFPTDateSpan
    TaxEntity: str = Field(..., min_length=1, max_length=20)
    ProductCompanyTaxID: str = Field(..., min_length=1, max_length=30)
    SoftwareCertificateNumber: int = Field(..., ge=0) # nonNegativeInteger
    ProductID: str = Field(..., min_length=3, max_length=255, pattern=r"^[^/]+/[^/]+$") # SAFPTProductID
    ProductVersion: str = Field(..., min_length=1, max_length=30)
    HeaderComment: Optional[str] = Field(None, min_length=1, max_length=255)
    Telephone: Optional[str] = Field(None, min_length=1, max_length=20)
    Fax: Optional[str] = Field(None, min_length=1, max_length=20)
    Email: Optional[EmailStr] = None # Pydantic's EmailStr for basic validation
    Website: Optional[str] = Field(None, min_length=1, max_length=60)

    @validator('CompanyID')
    def validate_company_id(cls, value):
        import re
        if not re.match(r"^(?:[0-9]{9}|[^ ]+ [0-9/]+)$", value):
            raise ValueError('CompanyID must be a 9-digit NIF or "Conservatoria Registo Comercial" format')
        return value

    @validator('ProductCompanyTaxID')
    def validate_product_company_tax_id(cls, value):
        import re
        if not re.match(r"^(?:[0-9]{9}|Global)$", value):
            raise ValueError('ProductCompanyTaxID must be a 9-digit NIF or "Global"')
        return value

    @validator('EndDate')
    def validate_end_date_after_start_date(cls, value, values):
        if 'StartDate' in values and value < values['StartDate']:
            raise ValueError('EndDate must be after or the same as StartDate')
        return value

    # Ensure other simple type definitions are updated if they are used by Header
    # For example, PostalCode in AddressStructure could have a validator for PT format.
    # For Country in AddressStructure, ensure it's a valid ISO 3166-1 alpha-2 code.

class GroupingCategoryEnum(str, Enum):
    GR = "GR"  # 1st degree GL account
    GA = "GA"  # Aggregator GL account
    GM = "GM"  # Movement GL account
    AR = "AR"  # 1st degree Analytical account
    AA = "AA"  # Aggregator Analytical account
    AM = "AM"  # Movement Analytical account

class GeneralLedgerAccount(BaseModel):
    AccountID: SAFPTGLAccountID = Field(..., min_length=2, max_length=30)
    AccountDescription: str = Field(..., min_length=1, max_length=100)
    OpeningDebitBalance: SAFMonetaryType = Field(..., ge=0.0)
    OpeningCreditBalance: SAFMonetaryType = Field(..., ge=0.0)
    ClosingDebitBalance: SAFMonetaryType = Field(..., ge=0.0)
    ClosingCreditBalance: SAFMonetaryType = Field(..., ge=0.0)
    GroupingCategory: GroupingCategoryEnum
    GroupingCode: Optional[SAFPTGLAccountID] = Field(None, min_length=2, max_length=30)
    TaxonomyCode: Optional[int] = Field(None, ge=1, le=999)

    @model_validator(mode='after')
    def check_assertions(self) -> 'GeneralLedgerAccount':
        # TaxonomyCode presence based on GroupingCategory
        is_gm = (self.GroupingCategory == GroupingCategoryEnum.GM)
        taxonomy_code_present = (self.TaxonomyCode is not None)
        if is_gm and not taxonomy_code_present:
            raise ValueError("TaxonomyCode must be present if GroupingCategory is GM.")
        # This condition is slightly different from XSD:
        # XSD: (ns:GroupingCategory != 'GM' and not(ns:TaxonomyCode)) or (ns:GroupingCategory eq 'GM' and ns:TaxonomyCode)
        # This means if not GM, TaxonomyCode MUST NOT be present.
        # And if GM, TaxonomyCode MUST be present.
        if not is_gm and taxonomy_code_present:
             raise ValueError("TaxonomyCode must not be present if GroupingCategory is not GM.")

        # GroupingCode presence based on GroupingCategory
        grouping_code_present = (self.GroupingCode is not None)
        category_requires_grouping_code = self.GroupingCategory in [
            GroupingCategoryEnum.GA, GroupingCategoryEnum.AA,
            GroupingCategoryEnum.GM, GroupingCategoryEnum.AM
        ]
        # XSD: (ns:GroupingCategory eq 'GR' and not(ns:GroupingCode)) or (ns:GroupingCategory eq 'AR' and not(ns:GroupingCode)) or ...
        # This means for GR and AR, GroupingCode MUST NOT be present.
        category_prohibits_grouping_code = self.GroupingCategory in [
            GroupingCategoryEnum.GR, GroupingCategoryEnum.AR
        ]
        if category_requires_grouping_code and not grouping_code_present:
            raise ValueError(f"GroupingCode must be present for GroupingCategory {self.GroupingCategory.value}.")
        if category_prohibits_grouping_code and grouping_code_present:
            raise ValueError(f"GroupingCode must not be present for GroupingCategory {self.GroupingCategory.value}.")
        return self

class Customer(BaseModel):
    CustomerID: str = Field(..., min_length=1, max_length=30)
    AccountID: SAFPTGLAccountID = Field(..., min_length=1, max_length=30)
    CustomerTaxID: str = Field(..., min_length=1, max_length=30)
    CompanyName: str = Field(..., min_length=1, max_length=100)
    Contact: Optional[str] = Field(None, min_length=1, max_length=50)
    BillingAddress: CustomerAddressStructure
    ShipToAddress: Optional[List[CustomerAddressStructure]] = None
    Telephone: Optional[str] = Field(None, min_length=1, max_length=20)
    Fax: Optional[str] = Field(None, min_length=1, max_length=20)
    Email: Optional[EmailStr] = None
    Website: Optional[str] = Field(None, min_length=1, max_length=60)
    SelfBillingIndicator: int

    @validator('CustomerTaxID')
    def validate_customer_tax_id(cls, value):
        import re
        if not re.match(r"^(?:[0-9]{9}|999999990|Consumidor final)$", value):
            raise ValueError('CustomerTaxID must be a 9-digit NIF, "999999990", or "Consumidor final".')
        return value

    @validator('SelfBillingIndicator')
    def validate_self_billing_indicator(cls, value):
        if value not in [0, 1]:
            raise ValueError('SelfBillingIndicator must be 0 or 1.')
        return value

class Supplier(BaseModel):
    SupplierID: str = Field(..., min_length=1, max_length=30)
    AccountID: SAFPTGLAccountID = Field(..., min_length=1, max_length=30)
    SupplierTaxID: str = Field(..., min_length=9, max_length=9) # Portuguese NIF is 9 digits
    CompanyName: str = Field(..., min_length=1, max_length=100)
    Contact: Optional[str] = Field(None, min_length=1, max_length=50)
    BillingAddress: AddressStructure
    ShipFromAddress: Optional[List[AddressStructure]] = None
    Telephone: Optional[str] = Field(None, min_length=1, max_length=20)
    Fax: Optional[str] = Field(None, min_length=1, max_length=20)
    Email: Optional[EmailStr] = None
    Website: Optional[str] = Field(None, min_length=1, max_length=60)
    SelfBillingIndicator: int

    @validator('SupplierTaxID')
    def validate_supplier_tax_id(cls, value):
        import re
        if not re.match(r"^[0-9]{9}$", value): # Must be a 9-digit NIF
            raise ValueError('SupplierTaxID must be a 9-digit Portuguese NIF.')
        return value

    @validator('SelfBillingIndicator')
    def validate_self_billing_indicator(cls, value):
        if value not in [0, 1]:
            raise ValueError('SelfBillingIndicator must be 0 or 1.')
        return value

class ProductTypeEnum(str, Enum):
    PRODUTOS = "P"
    SERVICOS = "S"
    OUTROS = "O"
    IMPOSTOS_ESPECIAIS_CONSUMO = "E"
    IMPOSTOS_TAXAS_ENCARGOS = "I"

class Product(BaseModel):
    ProductType: ProductTypeEnum
    ProductCode: str = Field(..., min_length=1, max_length=60)
    ProductGroup: Optional[str] = Field(None, min_length=1, max_length=50) # If present, not empty
    ProductDescription: str = Field(..., min_length=2, max_length=200)
    ProductNumberCode: str = Field(..., min_length=1, max_length=60)
    # CustomsDetails: Optional[CustomsDetails] # Remains out of scope for now

class TaxTypeEnum(str, Enum):
    IVA = "IVA"  # Value Added Tax
    IS = "IS"   # Stamp Duty
    NS = "NS"   # Not subject to tax / No tax (typically for tax representation in specific docs)

class TaxTableEntry(BaseModel):
    TaxType: TaxTypeEnum
    TaxCountryRegion: str = Field(..., pattern=r"^([A-Z]{2}|PT-AC|PT-MA)$")
    TaxCode: str = Field(..., min_length=1, max_length=10)
    Description: str = Field(..., min_length=1, max_length=255)
    TaxExpirationDate: Optional[SAFPTDateSpan] = None
    TaxPercentage: Optional[SAFDecimalType] = Field(None, ge=0.0)
    TaxAmount: Optional[SAFMonetaryType] = Field(None, ge=0.0)

    @model_validator(mode='after')
    def check_tax_percentage_or_amount(self) -> 'TaxTableEntry':
        percentage_present = self.TaxPercentage is not None
        amount_present = self.TaxAmount is not None

        if percentage_present and amount_present:
            raise ValueError("TaxPercentage and TaxAmount cannot both be present.")
        if not percentage_present and not amount_present:
            raise ValueError("Either TaxPercentage or TaxAmount must be present.")
        return self

class TaxTable(BaseModel):
    TaxTableEntry: List[TaxTableEntry] # This model itself is fine

class MasterFiles(BaseModel):
    GeneralLedgerAccounts: Optional[List[GeneralLedgerAccount]] = None # Original XSD: minOccurs="0", but has Account element maxOccurs="unbounded". Pydantic needs List if present.
    Customer: Optional[List[Customer]] = None
    Supplier: Optional[List[Supplier]] = None
    Product: Optional[List[Product]] = None
    TaxTable: Optional[TaxTable] = None # Original XSD: minOccurs="0"

# Forward declaration for Line types if they are complex and defined later
# class DebitLine(BaseModel): ...
# class CreditLine(BaseModel): ...

class TransactionLines(BaseModel):
    # DebitLine: List[DebitLine] # Define DebitLine model later
    # CreditLine: List[CreditLine] # Define CreditLine model later
    pass # Placeholder

class Transaction(BaseModel):
    TransactionID: SAFPTTransactionID
    Period: int # SAFPTAccountingPeriod (1-16)
    TransactionDate: SAFPTDateSpan
    SourceID: str = Field(..., max_length=30)
    Description: str = Field(..., max_length=200)
    DocArchivalNumber: str # SAFTPTDocArchivalNumber (max_length=20, no spaces)
    TransactionType: str # Enum: N, R, A, J
    GLPostingDate: SAFPTDateSpan
    CustomerID: Optional[str] = Field(None, max_length=30)
    SupplierID: Optional[str] = Field(None, max_length=30)
    Lines: TransactionLines # Placeholder, will be detailed

    # TODO: Validator for CustomerID or SupplierID choice

class Journal(BaseModel):
    JournalID: SAFPTJournalID
    Description: str = Field(..., max_length=200)
    Transaction: Optional[List[Transaction]] = None

class GeneralLedgerEntries(BaseModel):
    NumberOfEntries: int = Field(..., ge=0)
    TotalDebit: SAFMonetaryType
    TotalCredit: SAFMonetaryType
    Journal: Optional[List[Journal]] = None

# Define specific document types like SalesInvoice, StockMovement etc. later
# class SalesInvoice(BaseModel): ...
# class StockMovement(BaseModel): ...
# class WorkDocument(BaseModel): ...
# class Payment(BaseModel): ...

class SalesInvoices(BaseModel):
    NumberOfEntries: int = Field(..., ge=0)
    TotalDebit: SAFMonetaryType
    TotalCredit: SAFMonetaryType
    # Invoice: Optional[List[SalesInvoice]] = None # Define SalesInvoice model later

class MovementOfGoods(BaseModel):
    NumberOfMovementLines: int = Field(..., ge=0)
    TotalQuantityIssued: SAFDecimalType
    # StockMovement: Optional[List[StockMovement]] = None # Define StockMovement model later

class WorkingDocuments(BaseModel):
    NumberOfEntries: int = Field(..., ge=0)
    TotalDebit: SAFMonetaryType
    TotalCredit: SAFMonetaryType
    # WorkDocument: Optional[List[WorkDocument]] = None # Define WorkDocument model later

class Payments(BaseModel):
    NumberOfEntries: int = Field(..., ge=0)
    TotalDebit: SAFMonetaryType
    TotalCredit: SAFMonetaryType
    # Payment: Optional[List[Payment]] = None # Define Payment model later

class SourceDocuments(BaseModel):
    SalesInvoices: Optional[SalesInvoices] = None
    MovementOfGoods: Optional[MovementOfGoods] = None
    WorkingDocuments: Optional[WorkingDocuments] = None
    Payments: Optional[Payments] = None

class AuditFile(BaseModel):
    Header: Header
    MasterFiles: MasterFiles # In XSD, MasterFiles itself is not optional, but its children are.
    GeneralLedgerEntries: Optional[GeneralLedgerEntries] = None
    SourceDocuments: Optional[SourceDocuments] = None

    # TODO: Add XSD unique constraints and keyrefs as validators if possible/practical with Pydantic
