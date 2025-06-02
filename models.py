from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field as PydanticField, validator, condecimal, model_validator
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

# Helper function for validating string length
def check_length(value: Optional[str], max_length: int, min_length: int = 1) -> Optional[str]:
    if value is None:
        return value
    if not (min_length <= len(value) <= max_length):
        raise ValueError(f"Length must be between {min_length} and {max_length} characters.")
    return value

# SAF-T PT Custom Types & Enums

# Monetary type: Decimal with 2 decimal places, minInclusive 0.00
SAFmonetaryType = condecimal(ge=Decimal('0.00'), decimal_places=2)

class SAFdateTimeType(datetime):
    # Pydantic handles datetime parsing and validation by default.
    # Additional specific validation can be added if needed.
    pass

class SAFPTDateSpan(date):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, (date, str)):
            raise TypeError('Invalid type for date')
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError('Invalid date format')
        if not (date(2000, 1, 1) <= value <= date(9999, 12, 31)):
            raise ValueError("Date out of allowed range (2000-01-01 to 9999-12-31)")
        return value

class SAFPTGLAccountID(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, str):
            raise TypeError('String required')
        # Pattern: ([^^]*) - any character except ^
        if "^" in value:
            raise ValueError("AccountID cannot contain '^'")
        check_length(value, max_length=30, min_length=2)
        return value

class SAFPTtextTypeMandatoryMax10Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 10)

class SAFPTtextTypeMandatoryMax20Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 20)

class SAFPTtextTypeMandatoryMax30Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 30)

class SAFPTtextTypeMandatoryMax50Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 50)

class SAFPTtextTypeMandatoryMax60Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 60)

class SAFPTtextTypeMandatoryMax100Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 100)

class SAFPTtextTypeMandatoryMax200Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 200)

class SAFPTtextTypeMandatoryMax210Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 210)
        
class SAFPTtextTypeMandatoryMax254Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 254)

class SAFPTtextTypeMandatoryMax255Car(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        return check_length(value, 255)

class SAFPTPortugueseVatNumber(int):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, int):
            raise TypeError('Integer required')
        if not (100000000 <= value <= 999999999):
            raise ValueError("Portuguese VAT number must be 9 digits long and not start with 0.")
        return value
        
class CurrencyPT(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        if value != "EUR":
            raise ValueError("CurrencyCode must be EUR")
        return value

class AuditFileVersion(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        if value != "1.04_01":
            raise ValueError("AuditFileVersion must be 1.04_01")
        return value

TaxAccountingBasisEnum = Literal["C", "E", "F", "I", "P", "R", "S", "T"]

class CompanyIDType(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        # Simplified pattern for now: ([0-9]{9})+|([^^]+ [0-9/]+)
        # This means either 9 digits or some characters followed by space and numbers/slash
        import re
        if not (re.fullmatch(r"[0-9]{9}", value) or re.fullmatch(r"[^^]+ [0-9/]+", value)):
            raise ValueError("Invalid CompanyID format")
        check_length(value, max_length=50)
        return value

class ProductIDType(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        # Pattern: [^/]+/[^/]+
        if "/" not in value or value.startswith("/") or value.endswith("/"):
            raise ValueError("ProductID must be in format 'part1/part2'")
        check_length(value, max_length=255, min_length=3)
        return value

class CountryType(str):
    # A very long list of ISO 3166-1 alpha-2 codes. For simplicity, we'll just check length.
    # In a real scenario, a proper validation against the list would be better.
    # For now, only PT, PT-AC, PT-MA are explicitly listed in XSD for TaxCountryRegion
    # We will use a generic 2-letter for Country and CustomerCountry for now.
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        if len(value) != 2 or not value.isalpha() or not value.isupper():
            raise ValueError("Country must be a 2-letter uppercase ISO 3166-1 alpha-2 code.")
        # Consider adding a list of valid ISO codes if strictness is needed.
        return value

TaxCountryRegionType = Literal[
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
    "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
    "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF",
    "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM",
    "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG",
    "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS",
    "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO",
    "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "XK", "YE", "YT", "ZA", "ZM", "ZW", "PT-AC", "PT-MA"
]


class CustomerCountry(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        if value == "Desconhecido":
            return value
        # Reuse CountryType validation for actual country codes
        try:
            CountryType.validate(value)
        except ValueError:
            raise ValueError("Country must be a 2-letter uppercase ISO 3166-1 alpha-2 code or 'Desconhecido'.")
        return value

GroupingCategoryEnum = Literal["GR", "GA", "GM", "AR", "AA", "AM"]
TaxonomyReferenceEnum = Literal["S", "M", "N", "O"]
ProductTypeEnum = Literal["P", "S", "O", "E", "I"]
TaxTypeEnum = Literal["IVA", "IS", "NS"] # For TaxTableEntry and Tax (in SalesInvoices, etc.)
MovementTaxTypeEnum = Literal["IVA", "NS"] # For MovementTax

class SAFPTTaxonomyCode(int):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, int):
            raise TypeError('Integer required for TaxonomyCode')
        if not (1 <= value <= 999):
            raise ValueError('TaxonomyCode must be between 1 and 999.')
        return value

class TaxTableEntryTaxCode(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        check_length(value, max_length=10)
        # Pattern: RED|INT|NOR|ISE|OUT|([a-zA-Z0-9\.])*|NS|NA
        # This is a complex pattern, for now, we check length and common values.
        # A more robust regex could be added.
        if value not in ["RED", "INT", "NOR", "ISE", "OUT", "NS", "NA"] and not all(c.isalnum() or c == '.' for c in value):
            raise ValueError("Invalid TaxTableEntryTaxCode format.")
        return value

class SAFPTCNCode(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 8:
            raise ValueError("SAFPTCNCode must be 8 digits.")
        return value

class SAFPTUNNumber(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 4:
            raise ValueError("SAFPTUNNumber must be 4 digits.")
        return value


# Complex Types
class AddressStructure(BaseModel):
    BuildingNumber: Optional[SAFPTtextTypeMandatoryMax10Car] = None
    StreetName: Optional[SAFPTtextTypeMandatoryMax200Car] = None
    AddressDetail: SAFPTtextTypeMandatoryMax210Car
    City: SAFPTtextTypeMandatoryMax50Car
    PostalCode: SAFPTtextTypeMandatoryMax20Car # Add pattern validation later
    Region: Optional[SAFPTtextTypeMandatoryMax50Car] = None
    Country: CountryType

class CustomerAddressStructure(BaseModel): # This remains Pydantic for now
    BuildingNumber: Optional[SAFPTtextTypeMandatoryMax10Car] = None
    StreetName: Optional[SAFPTtextTypeMandatoryMax200Car] = None
    AddressDetail: SAFPTtextTypeMandatoryMax210Car
    City: SAFPTtextTypeMandatoryMax50Car
    PostalCode: SAFPTtextTypeMandatoryMax20Car 
    Region: Optional[SAFPTtextTypeMandatoryMax50Car] = None
    Country: CustomerCountry


# Main Models
class Header(BaseModel): # Not a DB table for now
    AuditFileVersion: AuditFileVersion
    CompanyID: CompanyIDType
    TaxRegistrationNumber: SAFPTPortugueseVatNumber
    TaxAccountingBasis: TaxAccountingBasisEnum
    CompanyName: SAFPTtextTypeMandatoryMax100Car
    BusinessName: Optional[SAFPTtextTypeMandatoryMax60Car] = None
    CompanyAddress: AddressStructure
    FiscalYear: int = PydanticField(ge=2000, le=9999)
    StartDate: SAFPTDateSpan
    EndDate: SAFPTDateSpan
    CurrencyCode: CurrencyPT
    DateCreated: SAFPTDateSpan
    TaxEntity: SAFPTtextTypeMandatoryMax20Car
    ProductCompanyTaxID: SAFPTtextTypeMandatoryMax30Car
    SoftwareCertificateNumber: int = PydanticField(ge=0)
    ProductID: ProductIDType
    ProductVersion: SAFPTtextTypeMandatoryMax30Car
    HeaderComment: Optional[SAFPTtextTypeMandatoryMax255Car] = None
    Telephone: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Fax: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Email: Optional[SAFPTtextTypeMandatoryMax254Car] = None
    Website: Optional[SAFPTtextTypeMandatoryMax60Car] = None

# --- User Model (for Authentication) ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column("username", unique=True, index=True, nullable=False))
    email: Optional[str] = Field(default=None, sa_column=Column("email", unique=True, index=True))
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    # Relationship to Customer (User can own multiple Customers)
    # customers: List["Customer"] = Relationship(back_populates="owner") 
    # For now, focusing on owner_id in Customer. Full Relationship can be added later if needed.


# --- SQLModel Table Models (MasterFiles etc.) ---
class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    CustomerID: SAFPTtextTypeMandatoryMax30Car = Field(index=True, unique=True)
    AccountID: Union[SAFPTGLAccountID, Literal["Desconhecido"]]
    CustomerTaxID: SAFPTtextTypeMandatoryMax30Car = Field(index=True)
    CompanyName: SAFPTtextTypeMandatoryMax100Car
    Contact: Optional[SAFPTtextTypeMandatoryMax50Car] = None
    
    BillingAddress: CustomerAddressStructure = Field(sa_column=Column(JSON))
    ShipToAddress: Optional[List[CustomerAddressStructure]] = Field(default=None, sa_column=Column(JSON))
        
    Telephone: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Fax: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Email: Optional[SAFPTtextTypeMandatoryMax254Car] = None
    Website: Optional[SAFPTtextTypeMandatoryMax60Car] = None
    SelfBillingIndicator: int = Field(default=0)

    # Link to User table
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)
    # owner: Optional[User] = Relationship(back_populates="customers")
    # Deferring full Relationship object to avoid immediate complexity with circular refs.
    # owner_id is the critical part for DB schema.


class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    SupplierID: SAFPTtextTypeMandatoryMax30Car = Field(index=True, unique=True)
    AccountID: Union[SAFPTGLAccountID, Literal["Desconhecido"]]
    SupplierTaxID: SAFPTtextTypeMandatoryMax30Car = Field(index=True)
    CompanyName: SAFPTtextTypeMandatoryMax100Car
    Contact: Optional[SAFPTtextTypeMandatoryMax50Car] = None

    BillingAddress: AddressStructure = Field(sa_column=Column(JSON)) 
    ShipFromAddress: Optional[List[AddressStructure]] = Field(default=None, sa_column=Column(JSON)) 

    Telephone: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Fax: Optional[SAFPTtextTypeMandatoryMax20Car] = None
    Email: Optional[SAFPTtextTypeMandatoryMax254Car] = None
    Website: Optional[SAFPTtextTypeMandatoryMax60Car] = None
    SelfBillingIndicator: int = Field(default=0)


class Account(SQLModel, table=True): 
    __tablename__ = "generalledgeraccount" 
    id: Optional[int] = Field(default=None, primary_key=True)
    AccountID: SAFPTGLAccountID = Field(unique=True, index=True) 
    AccountDescription: SAFPTtextTypeMandatoryMax100Car
    OpeningDebitBalance: SAFmonetaryType
    OpeningCreditBalance: SAFmonetaryType
    ClosingDebitBalance: SAFmonetaryType
    ClosingCreditBalance: SAFmonetaryType
    GroupingCategory: GroupingCategoryEnum
    GroupingCode: Optional[SAFPTGLAccountID] = Field(default=None, index=True) 
    TaxonomyCode: Optional[SAFPTTaxonomyCode] = Field(default=None, index=True)

    # XSD asserts:
    # if ((ns:GroupingCategory != 'GM' and not(ns:TaxonomyCode)) or (ns:GroupingCategory eq 'GM' and ns:TaxonomyCode)) then true() else false()
    # if ((ns:GroupingCategory eq 'GR' and not(ns:GroupingCode)) or (ns:GroupingCategory eq 'AR' and not(ns:GroupingCode)) or (ns:GroupingCategory eq 'GA' and ns:GroupingCode) or (ns:GroupingCategory eq 'AA' and ns:GroupingCode) or (ns:GroupingCategory eq 'GM' and ns:GroupingCode) or (ns:GroupingCategory eq 'AM' and ns:GroupingCode)) then true() else false()"
    # These complex validations can be implemented with root_validators if necessary.

class GeneralLedgerAccounts(BaseModel): # Not a table itself
    TaxonomyReference: TaxonomyReferenceEnum
    Account: List[Account] 

class CustomsDetails(BaseModel): # Remains Pydantic, could be JSON in Product
    CNCode: Optional[List[SAFPTCNCode]] = None 
    UNNumber: Optional[List[SAFPTUNNumber]] = None

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ProductType: ProductTypeEnum
    ProductCode: SAFPTtextTypeMandatoryMax60Car = Field(unique=True, index=True) 
    ProductGroup: Optional[SAFPTtextTypeMandatoryMax50Car] = None
    ProductDescription: SAFPTtextTypeMandatoryMax200Car 
    ProductNumberCode: SAFPTtextTypeMandatoryMax60Car
    CustomsDetails: Optional[CustomsDetails] = Field(default=None, sa_column=Column(JSON)) 


# TaxTableEntry and TaxTable remain Pydantic for now, not converting to SQLModel tables in this step.
class TaxTableEntry(BaseModel):
    TaxType: TaxTypeEnum
    TaxCountryRegion: TaxCountryRegionType
    TaxCode: TaxTableEntryTaxCode 
    Description: SAFPTtextTypeMandatoryMax255Car
    TaxExpirationDate: Optional[SAFPTDateSpan] = None 
    TaxPercentage: Optional[condecimal(ge=Decimal('0.00'))] = None 
    TaxAmount: Optional[SAFmonetaryType] = None

    # Simplified field validator, main logic in model_validator
    @validator('TaxPercentage', 'TaxAmount', pre=False, always=True) 
    def check_individual_tax_fields(cls, v, values, field):
        # This validator is now less critical for cross-field, but can check individual constraints if any
        return v
    
    @model_validator(mode='after')
    def check_tax_rules(self) -> 'TaxTableEntry':
        if self.TaxPercentage is None and self.TaxAmount is None:
            raise ValueError('Either TaxPercentage or TaxAmount must be provided.')
        if self.TaxPercentage is not None and self.TaxAmount is not None:
            raise ValueError('TaxPercentage and TaxAmount cannot both have values.')
        return self


class TaxTable(BaseModel): # Not a table
    TaxTableEntry: List[TaxTableEntry] 


class MasterFiles(BaseModel): # Not a table
    GeneralLedgerAccounts: Optional[GeneralLedgerAccounts] = None 
    Customer: Optional[List[Customer]] = None # List of SQLModel table instances
    Supplier: Optional[List[Supplier]] = None # List of SQLModel table instances
    Product: Optional[List[Product]] = None   # List of SQLModel table instances
    TaxTable: Optional[TaxTable] = None 

# GeneralLedgerEntries Models (Not converting to SQLModel tables in this step)
class SAFPTAccountingPeriod(int):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, int):
            raise TypeError('Integer required for AccountingPeriod')
        if not (1 <= value <= 16): # As per XSD minInclusive 1, maxInclusive 16
            raise ValueError('SAFPTAccountingPeriod must be between 1 and 16.')
        return value

class SAFPTTransactionID(str): # Complex pattern, basic length check for now
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        # Pattern: [1-9][0-9]{3}-[01][0-9]-[0-3][0-9] [^ ]{1,30} [^ ]{1,20}
        # Example: 2023-10-26 JournalEntry1 Doc123
        # For now, just check length and basic structure
        parts = value.split(" ")
        if len(parts) < 3:
             raise ValueError("SAFPTTransactionID should have at least 3 parts separated by spaces.")
        try:
            datetime.strptime(parts[0], "%Y-%m-%d")
        except ValueError:
            raise ValueError("SAFPTTransactionID date part is invalid.")
        check_length(value, max_length=70)
        return value

TransactionTypeEnum = Literal["N", "R", "A", "J"]

class SAFPTJournalID(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        # Pattern: [^ ]{1,30} (no spaces, 1 to 30 chars)
        if " " in value:
            raise ValueError("SAFPTJournalID cannot contain spaces.")
        check_length(value, max_length=30)
        return value

class SAFTPTDocArchivalNumber(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, value: str) -> str:
        # Pattern: [^ ]{1,20} (no spaces, 1 to 20 chars)
        if " " in value:
            raise ValueError("SAFTPTDocArchivalNumber cannot contain spaces.")
        check_length(value, max_length=20)
        return value

SAFPTRecordID = SAFPTtextTypeMandatoryMax30Car 
SAFPTSourceDocumentID = SAFPTtextTypeMandatoryMax60Car 

class DebitLine(BaseModel):
    RecordID: SAFPTRecordID
    AccountID: SAFPTGLAccountID 
    SourceDocumentID: Optional[SAFPTSourceDocumentID] = None 
    SystemEntryDate: SAFdateTimeType
    Description: SAFPTtextTypeMandatoryMax200Car
    DebitAmount: SAFmonetaryType

class CreditLine(BaseModel):
    RecordID: SAFPTRecordID
    AccountID: SAFPTGLAccountID 
    SourceDocumentID: Optional[SAFPTSourceDocumentID] = None 
    SystemEntryDate: SAFdateTimeType
    Description: SAFPTtextTypeMandatoryMax200Car
    CreditAmount: SAFmonetaryType

class Lines(BaseModel):
    DebitLine: List[DebitLine] 
    CreditLine: List[CreditLine] 

    @validator('DebitLine', 'CreditLine', pre=True, always=True)
    def ensure_list(cls, v):
        return v if v is not None else []

class Transaction(BaseModel):
    TransactionID: SAFPTTransactionID 
    Period: SAFPTAccountingPeriod
    TransactionDate: SAFPTDateSpan 
    SourceID: SAFPTtextTypeMandatoryMax30Car
    Description: SAFPTtextTypeMandatoryMax200Car
    DocArchivalNumber: SAFTPTDocArchivalNumber
    TransactionType: TransactionTypeEnum
    GLPostingDate: SAFPTDateSpan 
    CustomerID: Optional[SAFPTtextTypeMandatoryMax30Car] = None 
    SupplierID: Optional[SAFPTtextTypeMandatoryMax30Car] = None 
    Lines: Lines

    @validator('CustomerID', 'SupplierID', pre=False, always=True) 
    def check_customer_supplier_exclusivity(cls, v, values, field):
        if field.name == 'CustomerID' and v is not None and values.get('SupplierID') is not None:
            raise ValueError('CustomerID and SupplierID cannot both have values in a Transaction.')
        if field.name == 'SupplierID' and v is not None and values.get('CustomerID') is not None:
            raise ValueError('CustomerID and SupplierID cannot both have values in a Transaction.')
        return v

class Journal(BaseModel):
    JournalID: SAFPTJournalID # Unique constraint
    Description: SAFPTtextTypeMandatoryMax200Car
    Transaction: Optional[List[Transaction]] = None # minOccurs="0", maxOccurs="unbounded"

class GeneralLedgerEntries(BaseModel):
    NumberOfEntries: int = Field(ge=0) # XSD: xs:nonNegativeInteger
    TotalDebit: SAFmonetaryType
    TotalCredit: SAFmonetaryType
    Journal: Optional[List[Journal]] = None # minOccurs="0", maxOccurs="unbounded"


class AuditFile(BaseModel):
    Header: Header
    MasterFiles: MasterFiles
    GeneralLedgerEntries: Optional[GeneralLedgerEntries] = None # minOccurs="0"
    # SourceDocuments: Optional[SourceDocuments] = None # To be implemented

# TODO: Implement the remaining models:
# - SourceDocuments (SalesInvoices, MovementOfGoods, WorkingDocuments, Payments and their sub-structures)
# TODO: Add more specific validation for patterns where appropriate (e.g. PostalCode, Telephone, Email, Website).
# TODO: Review all minOccurs="0" for Optional fields and maxOccurs="unbounded" for List fields - Done for current models.
# TODO: Validate DebitLine/CreditLine presence in Lines (at least one list should not be empty if Lines is present).
# TODO: Ensure all simple type restrictions from XSD are correctly mapped or validated. - Ongoing
# For example SAFPTAccountingPeriod, SAFPTTransactionID etc. - Done for current scope
# SAFmonetaryType should be Decimal with 2 decimal places and minInclusive 0.00 - Done
# SAFdateTimeType should be datetime - Done
# Add specific country code lists for Country and CustomerCountry if possible or use a library. - Partially done with Literal
# Add remaining enum types. - Done for current scope
# Implement XSD assertions for Account model using Pydantic root_validators.
print("Pydantic models updated in models.py")
