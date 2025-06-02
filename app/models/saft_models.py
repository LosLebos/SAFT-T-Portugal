from app import db
from datetime import datetime
from app.schemas.saft_data import TaxAccountingBasisEnum, CurrencyCodeEnum, ProductTypeEnum, GroupingCategoryEnum, TaxTypeEnum # Added TaxTypeEnum

class SaftHeaderData(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    audit_file_version = db.Column(db.String(10), nullable=False, default="1.04_01")
    company_id = db.Column(db.String(50), nullable=False)
    tax_registration_number = db.Column(db.Integer, nullable=False)
    tax_accounting_basis = db.Column(db.Enum(TaxAccountingBasisEnum), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(60), nullable=True)

    company_address_building_number = db.Column(db.String(10), nullable=True)
    company_address_street_name = db.Column(db.String(200), nullable=True)
    company_address_address_detail = db.Column(db.String(210), nullable=False)
    company_address_city = db.Column(db.String(50), nullable=False)
    company_address_postal_code = db.Column(db.String(20), nullable=False)
    company_address_region = db.Column(db.String(50), nullable=True)
    company_address_country = db.Column(db.String(2), nullable=False)

    fiscal_year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    currency_code = db.Column(db.Enum(CurrencyCodeEnum), nullable=False, default=CurrencyCodeEnum.EUR)
    date_created = db.Column(db.Date, nullable=False) # Date of SAF-T file creation
    tax_entity = db.Column(db.String(20), nullable=False)
    product_company_tax_id = db.Column(db.String(30), nullable=False)
    software_certificate_number = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.String(255), nullable=False)
    product_version = db.Column(db.String(30), nullable=False)

    header_comment = db.Column(db.Text, nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    website = db.Column(db.String(60), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('saft_header_data_entries', lazy='dynamic'))

    def __repr__(self):
        return f'<SaftHeaderData id={self.id} user_id={self.user_id} year={self.fiscal_year}>'

class MappingProfile(db.Model):
    __tablename__ = 'mapping_profile' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # user = db.relationship('User', backref=db.backref('mapping_profiles', lazy='dynamic'))
    # Relationship defined in User model via backref
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to FieldMapping (one-to-many)
    field_mappings = db.relationship('FieldMapping', backref='profile', lazy='dynamic', cascade="all, delete-orphan")

    # Unique constraint for profile name per user
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='uq_user_profile_name'),)

    def __repr__(self):
        return f'<MappingProfile {self.name} (User {self.user_id})>'

class FieldMapping(db.Model):
    __tablename__ = 'field_mapping' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('mapping_profile.id'), nullable=False)

    saft_internal_field = db.Column(db.String(255), nullable=False) # e.g., "Header.CompanyName"
    source_column_name = db.Column(db.String(255), nullable=False) # User's CSV/Excel column header
    default_value = db.Column(db.String(255), nullable=True)
    transformation_rule = db.Column(db.String(100), nullable=True) # e.g., "UPPERCASE", "DATE_FORMAT:YYYY-MM-DD"

    # Optional: created_at, updated_at if individual mapping changes need tracking
    # created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FieldMapping {self.saft_internal_field} -> {self.source_column_name} (Profile {self.profile_id})>'

class CustomerDb(db.Model):
    __tablename__ = 'customer_db' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # user = db.relationship('User', backref=db.backref('customers', lazy='dynamic')) # Define on User model side

    # Fields from Customer Pydantic Model
    customer_id_field = db.Column(db.String(30), nullable=False) # 'CustomerID' from Pydantic
    account_id = db.Column(db.String(30), nullable=False)    # SAFPTGLAccountID
    customer_tax_id = db.Column(db.String(30), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50), nullable=True)

    # Embedded BillingAddress fields
    billing_address_building_number = db.Column(db.String(10), nullable=True)
    billing_address_street_name = db.Column(db.String(200), nullable=True)
    billing_address_address_detail = db.Column(db.String(210), nullable=False)
    billing_address_city = db.Column(db.String(50), nullable=False)
    billing_address_postal_code = db.Column(db.String(20), nullable=False)
    billing_address_region = db.Column(db.String(50), nullable=True)
    billing_address_country = db.Column(db.String(20), nullable=False) # Max length for "Desconhecido" or ISO code

    # Embedded Primary ShippingAddress fields (Option A from plan)
    # Prefix with 'shipping_' to distinguish from billing address.
    shipping_address_building_number = db.Column(db.String(10), nullable=True)
    shipping_address_street_name = db.Column(db.String(200), nullable=True)
    shipping_address_address_detail = db.Column(db.String(210), nullable=True) # Optional if no shipping addr
    shipping_address_city = db.Column(db.String(50), nullable=True)
    shipping_address_postal_code = db.Column(db.String(20), nullable=True)
    shipping_address_region = db.Column(db.String(50), nullable=True)
    shipping_address_country = db.Column(db.String(20), nullable=True) # Max length for "Desconhecido" or ISO code

    telephone = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    website = db.Column(db.String(60), nullable=True)
    self_billing_indicator = db.Column(db.Integer, nullable=False) # 0 or 1

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for CustomerID per user
    __table_args__ = (db.UniqueConstraint('user_id', 'customer_id_field', name='uq_user_customer_id'),)

    def __repr__(self):
        return f'<CustomerDb {self.customer_id_field} (User {self.user_id})>'

class SupplierDb(db.Model):
    __tablename__ = 'supplier_db'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Fields from Supplier Pydantic Model
    supplier_id_field = db.Column(db.String(30), nullable=False) # 'SupplierID' from Pydantic
    account_id = db.Column(db.String(30), nullable=False)    # SAFPTGLAccountID
    supplier_tax_id = db.Column(db.String(9), nullable=False) # Portuguese NIF (9 digits)
    company_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50), nullable=True)

    # Embedded BillingAddress fields
    billing_address_building_number = db.Column(db.String(10), nullable=True)
    billing_address_street_name = db.Column(db.String(200), nullable=True)
    billing_address_address_detail = db.Column(db.String(210), nullable=False)
    billing_address_city = db.Column(db.String(50), nullable=False)
    billing_address_postal_code = db.Column(db.String(20), nullable=False)
    billing_address_region = db.Column(db.String(50), nullable=True)
    billing_address_country = db.Column(db.String(2), nullable=False) # ISO code

    # Embedded Primary ShipFromAddress fields
    ship_from_address_building_number = db.Column(db.String(10), nullable=True)
    ship_from_address_street_name = db.Column(db.String(200), nullable=True)
    ship_from_address_address_detail = db.Column(db.String(210), nullable=True)
    ship_from_address_city = db.Column(db.String(50), nullable=True)
    ship_from_address_postal_code = db.Column(db.String(20), nullable=True)
    ship_from_address_region = db.Column(db.String(50), nullable=True)
    ship_from_address_country = db.Column(db.String(2), nullable=True) # ISO code

    telephone = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    website = db.Column(db.String(60), nullable=True)
    self_billing_indicator = db.Column(db.Integer, nullable=False) # 0 or 1

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for SupplierID per user
    __table_args__ = (db.UniqueConstraint('user_id', 'supplier_id_field', name='uq_user_supplier_id'),)

    def __repr__(self):
        return f'<SupplierDb {self.supplier_id_field} (User {self.user_id})>'

class ProductDb(db.Model):
    __tablename__ = 'product_db'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Fields from Product Pydantic Model (excluding CustomsDetails)
    product_type = db.Column(db.Enum(ProductTypeEnum), nullable=False) # Using the Enum
    product_code = db.Column(db.String(60), nullable=False) # Corresponds to ProductCode in Pydantic
    product_group = db.Column(db.String(50), nullable=True)
    product_description = db.Column(db.String(200), nullable=False)
    product_number_code = db.Column(db.String(60), nullable=False) # e.g., EAN

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for ProductCode per user
    __table_args__ = (db.UniqueConstraint('user_id', 'product_code', name='uq_user_product_code'),)

    def __repr__(self):
        return f'<ProductDb {self.product_code} (User {self.user_id})>'

class GeneralLedgerAccountDb(db.Model):
    __tablename__ = 'gl_account_db'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Fields from GeneralLedgerAccount Pydantic Model
    account_id_field = db.Column(db.String(30), nullable=False) # Corresponds to AccountID in Pydantic
    account_description = db.Column(db.String(100), nullable=False)

    opening_debit_balance = db.Column(db.Float, nullable=False, default=0.0)
    opening_credit_balance = db.Column(db.Float, nullable=False, default=0.0)
    closing_debit_balance = db.Column(db.Float, nullable=False, default=0.0)
    closing_credit_balance = db.Column(db.Float, nullable=False, default=0.0)

    grouping_category = db.Column(db.Enum(GroupingCategoryEnum), nullable=False)
    grouping_code = db.Column(db.String(30), nullable=True) # Corresponds to SAFPTGLAccountID
    taxonomy_code = db.Column(db.Integer, nullable=True) # Range 1-999

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for AccountID per user
    __table_args__ = (db.UniqueConstraint('user_id', 'account_id_field', name='uq_user_gl_account_id'),)

    def __repr__(self):
        return f'<GeneralLedgerAccountDb {self.account_id_field} (User {self.user_id})>'

class TaxTableEntryDb(db.Model):
    __tablename__ = 'tax_table_entry_db'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Fields from TaxTableEntry Pydantic Model
    tax_type = db.Column(db.Enum(TaxTypeEnum), nullable=False)
    tax_country_region = db.Column(db.String(5), nullable=False) # Max length for "PT-AC" or ISO codes
    tax_code = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    tax_expiration_date = db.Column(db.Date, nullable=True)

    tax_percentage = db.Column(db.Float, nullable=True)
    tax_amount = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for a tax entry: user, type, region, code
    __table_args__ = (db.UniqueConstraint('user_id', 'tax_type', 'tax_country_region', 'tax_code', name='uq_user_tax_entry'),)

    def __repr__(self):
        return f'<TaxTableEntryDb {self.tax_code} (User {self.user_id})>'
