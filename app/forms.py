from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed # Added FileField, FileAllowed
from wtforms import StringField, IntegerField, DateField, SelectField, SubmitField, TextAreaField, FormField, FieldList, FloatField, ValidationError # Added FloatField, ValidationError
from wtforms.validators import DataRequired, Length, Optional, Regexp, Email, NumberRange

# Import Enums from Pydantic schemas to populate choices for SelectFields
# Assuming saft_data.py is in app/schemas/
from .schemas.saft_data import TaxAccountingBasisEnum, CurrencyCodeEnum, ProductTypeEnum, GroupingCategoryEnum, TaxTypeEnum # Added TaxTypeEnum
from app.mapping_fields import get_mappable_fields


class AddressForm(FlaskForm):
    # Note: In a real scenario, for optional fields in Pydantic that are part of a sub-model,
    # you might handle them differently, perhaps not making them DataRequired here unless always needed.
    # For now, mirroring the structure.
    BuildingNumber = StringField('Building Number', validators=[Optional(), Length(max=10)])
    StreetName = StringField('Street Name', validators=[Optional(), Length(max=200)])
    AddressDetail = StringField('Address Detail', validators=[DataRequired(), Length(max=210)])
    City = StringField('City', validators=[DataRequired(), Length(max=50)])
    PostalCode = StringField('Postal Code', validators=[DataRequired(), Length(max=20)]) # Add Regexp for PT format if known
    Region = StringField('Region', validators=[Optional(), Length(max=50)])
    Country = StringField(
            'Country',
            validators=[
                DataRequired(),
                Length(min=2, max=11), # Accommodate 'Desconhecido' and ISO codes
                Regexp(r"^([A-Z]{2}|Desconhecido)$", message="Must be a 2-letter ISO code or 'Desconhecido'.")
            ]
        )

class HeaderForm(FlaskForm):
    AuditFileVersion = StringField(
        'Audit File Version',
        validators=[DataRequired(), Regexp(r"^1\.04_01$", message="Must be 1.04_01")],
        default="1.04_01",
        render_kw={'readonly': True} # Usually fixed
    )
    CompanyID = StringField(
        'Company ID (NIF or Commercial Registry)',
        validators=[DataRequired(), Length(min=1, max=50),
                    Regexp(r"^(?:[0-9]{9}|[^ ]+ [0-9/]+)$",
                           message='Invalid Company ID format. Must be a 9-digit NIF or "Conservatoria Registo Comercial" format.')]
    )
    TaxRegistrationNumber = IntegerField(
        'Tax Registration Number (NIF)',
        validators=[DataRequired(), NumberRange(min=100000000, max=999999999, message="Must be a 9-digit NIF")]
    )
    TaxAccountingBasis = SelectField(
        'Tax Accounting Basis',
        choices=[(choice.value, choice.name.replace("_", " ").title()) for choice in TaxAccountingBasisEnum],
        validators=[DataRequired()]
    )
    CompanyName = StringField('Company Name', validators=[DataRequired(), Length(min=1, max=100)])
    BusinessName = StringField('Business Name (Optional)', validators=[Optional(), Length(min=1, max=60)])

    CompanyAddress_BuildingNumber = StringField('Company Address: Building No.', validators=[Optional(), Length(max=10)])
    CompanyAddress_StreetName = StringField('Company Address: Street', validators=[Optional(), Length(max=200)])
    CompanyAddress_AddressDetail = StringField('Company Address: Detail', validators=[DataRequired(), Length(max=210)])
    CompanyAddress_City = StringField('Company Address: City', validators=[DataRequired(), Length(max=50)])
    CompanyAddress_PostalCode = StringField('Company Address: Postal Code', validators=[DataRequired(), Length(max=20)])
    CompanyAddress_Region = StringField('Company Address: Region', validators=[Optional(), Length(max=50)])
    CompanyAddress_Country = StringField('Company Address: Country Code', validators=[DataRequired(), Length(min=2, max=2)])

    FiscalYear = IntegerField('Fiscal Year', validators=[DataRequired(), NumberRange(min=2000, max=9999)])
    StartDate = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    EndDate = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')

    CurrencyCode = SelectField(
        'Currency Code',
        choices=[(choice.value, choice.name) for choice in CurrencyCodeEnum],
        validators=[DataRequired()],
        default=CurrencyCodeEnum.EUR.value,
        render_kw={'readonly': True} # Usually fixed to EUR for SAFT-PT
    )
    DateCreated = DateField('Date Created (SAF-T File)', validators=[DataRequired()], format='%Y-%m-%d')
    TaxEntity = StringField('Tax Entity', validators=[DataRequired(), Length(min=1, max=20)])
    ProductCompanyTaxID = StringField(
        'Product Company Tax ID (Software Producer NIF or "Global")',
        validators=[DataRequired(), Length(min=1, max=30),
                    Regexp(r"^(?:[0-9]{9}|Global)$", message='Must be a 9-digit NIF or "Global"')]
    )
    SoftwareCertificateNumber = IntegerField(
        'Software Certificate Number',
        validators=[DataRequired(), NumberRange(min=0, message="Must be a non-negative integer")]
    )
    ProductID = StringField(
        'Product ID (Software Name/Version)',
        validators=[DataRequired(), Length(min=3, max=255),
                    Regexp(r"^[^/]+/[^/]+$", message='Format: ProductName/Version')]
    )
    ProductVersion = StringField('Product Version', validators=[DataRequired(), Length(min=1, max=30)])

    HeaderComment = TextAreaField('Header Comment (Optional)', validators=[Optional(), Length(min=1, max=255)])
    Telephone = StringField('Telephone (Optional)', validators=[Optional(), Length(min=1, max=20)])
    Fax = StringField('Fax (Optional)', validators=[Optional(), Length(min=1, max=20)])
    Email = StringField('Email (Optional)', validators=[Optional(), Email(), Length(min=1, max=254)])
    Website = StringField('Website (Optional)', validators=[Optional(), Length(min=1, max=60)])

    Submit = SubmitField('Save Header Data')


class CreateMappingProfileForm(FlaskForm):
    name = StringField(
        'Profile Name',
        validators=[DataRequired(), Length(min=3, max=100)],
        description="A unique name for this mapping profile."
    )
    description = TextAreaField(
        'Description (Optional)',
        validators=[Optional(), Length(max=500)],
        description="A brief description of what this profile is for."
    )
    submit = SubmitField('Create Profile')

class FieldMappingEntryForm(FlaskForm): # Renamed from FieldMappingForm to avoid confusion with a potential parent
    # This form represents a single row in the field mapping table.
    # It will be used with FieldList.
    # No CSRF for subforms managed by FieldList by default.
    # For dynamic adding, an empty "template" row might be useful in JS.

    # Dynamically populate choices when the form is instantiated or in the route
    saft_internal_field = SelectField(
        'SAF-T Internal Field',
        choices=[], # Choices will be populated in the route/view
        validators=[DataRequired()],
        description="Select the target SAF-T field."
    )
    source_column_name = StringField(
        'Your Source Column Name',
        validators=[DataRequired(), Length(max=255)],
        description="Header name of the column in your CSV/Excel file."
    )
    default_value = StringField(
        'Default Value (Optional)',
        validators=[Optional(), Length(max=255)],
        description="Value to use if your source column is empty."
    )
    # transformation_rule = StringField('Transformation Rule (Optional)', validators=[Optional(), Length(max=100)]) # For future

    # No submit button here as it's part of a list of forms

class EditMappingsForm(FlaskForm):
    # This form will manage the profile's name, description, and its list of field mappings.
    name = StringField(
        'Profile Name',
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    description = TextAreaField(
        'Description (Optional)',
        validators=[Optional(), Length(max=500)]
    )

    # FieldList will contain multiple instances of FieldMappingEntryForm
    mappings = FieldList(
        FormField(FieldMappingEntryForm),
        min_entries=1, # Start with at least one mapping row
        label="Field Mappings"
    )

    submit = SubmitField('Save Mappings')
    add_mapping_row = SubmitField('Add Another Mapping') # For non-JS row addition if needed
                                                        # Or handle with JS for better UX.

class FileUploadForm(FlaskForm):
    data_file = FileField(
        'Data File (CSV or Excel .xlsx)',
        validators=[
            DataRequired(message="Please select a file."),
            FileAllowed(['csv', 'xlsx'], 'Only CSV and Excel (.xlsx) files are allowed!')
        ],
        description="Upload your transactional data in CSV or Excel format."
    )
    submit = SubmitField('Upload File')

class CustomerForm(FlaskForm):
    customer_id_field = StringField( # Corresponds to CustomerID in Pydantic/XSD
        'Customer Internal ID',
        validators=[DataRequired(), Length(min=1, max=30)],
        description="Unique identifier for this customer in your system."
    )
    account_id = StringField( # SAFPTGLAccountID
        'GL Account ID',
        validators=[DataRequired(), Length(min=1, max=30)],
        description="General ledger account ID for this customer (e.g., from your chart of accounts)."
    )
    customer_tax_id = StringField(
        'Customer Tax ID (NIF/VAT)',
        validators=[
            DataRequired(),
            Length(min=1, max=30),
            Regexp(r"^(?:[0-9]{9}|999999990|Consumidor final)$",
                   message='Must be a 9-digit NIF, "999999990", or "Consumidor final".')
        ]
    )
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=1, max=100)])
    contact = StringField('Contact Person (Optional)', validators=[Optional(), Length(min=1, max=50)])

    billing_address = FormField(AddressForm, label='Billing Address')

    shipping_address = FormField(AddressForm, label='Shipping Address (Optional)')

    telephone = StringField('Telephone (Optional)', validators=[Optional(), Length(min=1, max=20)])
    fax = StringField('Fax (Optional)', validators=[Optional(), Length(min=1, max=20)])
    email = StringField('Email (Optional)', validators=[Optional(), Email(), Length(max=254)]) # Email validator handles format
    website = StringField('Website (Optional)', validators=[Optional(), Length(min=1, max=60)])
    self_billing_indicator = SelectField(
        'Self-Billing Indicator',
        choices=[(0, 'No'), (1, 'Yes')],
        coerce=int,
        validators=[DataRequired()]
    )
    submit = SubmitField('Save Customer')

class SupplierForm(FlaskForm):
    supplier_id_field = StringField( # Corresponds to SupplierID in Pydantic/XSD
        'Supplier Internal ID',
        validators=[DataRequired(), Length(min=1, max=30)],
        description="Unique identifier for this supplier in your system."
    )
    account_id = StringField( # SAFPTGLAccountID
        'GL Account ID',
        validators=[DataRequired(), Length(min=1, max=30)],
        description="General ledger account ID for this supplier."
    )
    supplier_tax_id = StringField(
        'Supplier Tax ID (NIF/VAT)',
        validators=[
            DataRequired(),
            Length(min=9, max=9), # Portuguese NIF is 9 digits
            Regexp(r"^[0-9]{9}$", message='Supplier Tax ID must be a 9-digit NIF.')
        ]
    )
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=1, max=100)])
    contact = StringField('Contact Person (Optional)', validators=[Optional(), Length(min=1, max=50)])

    billing_address = FormField(AddressForm, label='Billing Address')

    ship_from_address = FormField(AddressForm, label='Ship-From Address (Optional)')

    telephone = StringField('Telephone (Optional)', validators=[Optional(), Length(min=1, max=20)])
    fax = StringField('Fax (Optional)', validators=[Optional(), Length(min=1, max=20)])
    email = StringField('Email (Optional)', validators=[Optional(), Email(), Length(max=254)])
    website = StringField('Website (Optional)', validators=[Optional(), Length(min=1, max=60)])

    self_billing_indicator = SelectField(
        'Self-Billing Indicator',
        choices=[(0, 'No'), (1, 'Yes')],
        coerce=int,
        validators=[DataRequired()] # Ensure a choice is made
    )
    submit = SubmitField('Save Supplier')

class ProductForm(FlaskForm):
    product_type = SelectField(
        'Product Type',
        choices=[(choice.value, choice.name.replace("_", " ").title()) for choice in ProductTypeEnum],
        validators=[DataRequired()],
        description="Select the type of product or service."
    )
    product_code = StringField(
        'Product Code',
        validators=[DataRequired(), Length(min=1, max=60)],
        description="Unique code for this product/service."
    )
    product_group = StringField(
        'Product Group (Optional)',
        validators=[Optional(), Length(min=1, max=50)], # If provided, must not be empty
        description="Optional grouping category for the product."
    )
    product_description = TextAreaField( # Changed to TextAreaField for potentially longer descriptions
        'Product Description',
        validators=[DataRequired(), Length(min=2, max=200)],
        description="Detailed description of the product/service."
    )
    product_number_code = StringField(
        'Product Number Code (e.g., EAN)',
        validators=[DataRequired(), Length(min=1, max=60)],
        description="Standardized number code if applicable (e.g., EAN, UPC)."
    )
    submit = SubmitField('Save Product')

class GLAccountForm(FlaskForm):
    account_id_field = StringField( # Corresponds to AccountID in Pydantic/XSD
        'Account ID',
        validators=[DataRequired(), Length(min=2, max=30)],
        description="Unique identifier for this GL account (min 2, max 30 chars)."
    )
    account_description = StringField(
        'Account Description',
        validators=[DataRequired(), Length(min=1, max=100)],
        description="Description of the GL account."
    )
    opening_debit_balance = FloatField(
        'Opening Debit Balance',
        validators=[DataRequired(), NumberRange(min=0)],
        default=0.0,
        description="Must be a non-negative number."
    )
    opening_credit_balance = FloatField(
        'Opening Credit Balance',
        validators=[DataRequired(), NumberRange(min=0)],
        default=0.0,
        description="Must be a non-negative number."
    )
    closing_debit_balance = FloatField(
        'Closing Debit Balance',
        validators=[DataRequired(), NumberRange(min=0)],
        default=0.0,
        description="Must be a non-negative number."
    )
    closing_credit_balance = FloatField(
        'Closing Credit Balance',
        validators=[DataRequired(), NumberRange(min=0)],
        default=0.0,
        description="Must be a non-negative number."
    )
    grouping_category = SelectField(
        'Grouping Category',
        choices=[(choice.value, f"{choice.value} - {choice.name.replace('_', ' ').title()}") for choice in GroupingCategoryEnum],
        validators=[DataRequired()],
        description="Select the grouping category for this account."
    )
    grouping_code = StringField(
        'Grouping Code (Optional)',
        validators=[Optional(), Length(min=2, max=30)],
        description="Required for some grouping categories. Refers to another AccountID."
    )
    taxonomy_code = IntegerField(
        'Taxonomy Code (Optional)',
        validators=[Optional(), NumberRange(min=1, max=999)],
        description="Required for GM category, otherwise not allowed. Range 1-999."
    )
    submit = SubmitField('Save GL Account')

class TaxTableEntryForm(FlaskForm):
    tax_type = SelectField(
        'Tax Type',
        choices=[(choice.value, choice.name.replace("_", " ").title()) for choice in TaxTypeEnum],
        validators=[DataRequired()],
        description="Select the type of tax (IVA, IS, NS)."
    )
    tax_country_region = StringField(
        'Tax Country/Region',
        validators=[
            DataRequired(),
            Length(min=2, max=5), # Max 5 for "PT-AC"
            Regexp(r"^([A-Z]{2}|PT-AC|PT-MA)$",
                   message="Must be a 2-letter ISO code, or PT-AC (Azores), PT-MA (Madeira).")
        ],
        description="ISO Country Code or PT-AC/PT-MA."
    )
    tax_code = StringField(
        'Tax Code',
        validators=[DataRequired(), Length(min=1, max=10)],
        description="Tax code (e.g., NOR, ISE, RED, or other specific codes)."
    )
    description = StringField(
        'Description',
        validators=[DataRequired(), Length(min=1, max=255)],
        description="Description of the tax entry."
    )
    tax_expiration_date = DateField(
        'Tax Expiration Date (Optional)',
        validators=[Optional()],
        format='%Y-%m-%d',
        description="Date when this tax rate/amount expires, if applicable."
    )
    tax_percentage = FloatField(
        'Tax Percentage (e.g., 0.23 for 23%) (Optional)',
        validators=[Optional(), NumberRange(min=0, max=1, message="Percentage must be between 0.00 and 1.00 (e.g., 0.23 for 23%)")],
        description="Enter as a decimal (e.g., 0.23 for 23%). Leave blank if using Tax Amount."
    )
    tax_amount = FloatField(
        'Tax Amount (Fixed Value) (Optional)',
        validators=[Optional(), NumberRange(min=0)],
        default=0.0,
        description="Fixed tax amount. Leave blank if using Tax Percentage."
    )
    submit = SubmitField('Save Tax Entry')

    def validate(self, extra_validators=None):
        if not super(TaxTableEntryForm, self).validate(extra_validators):
            return False

        percentage_present = self.tax_percentage.data is not None
        amount_present = self.tax_amount.data is not None

        if percentage_present and amount_present:
            self.tax_percentage.errors.append("Tax Percentage and Tax Amount cannot both be present. Choose one.")
            self.tax_amount.errors.append("Tax Percentage and Tax Amount cannot both be present. Choose one.")
            return False
        if not percentage_present and not amount_present:
            self.tax_percentage.errors.append("Either Tax Percentage or Tax Amount must be provided.")
            self.tax_amount.errors.append("Either Tax Percentage or Tax Amount must be provided.")
            return False
        return True
