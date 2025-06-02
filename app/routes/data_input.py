from flask import Blueprint, render_template, request, redirect, url_for, flash, session # Added session back
from flask_login import current_user, login_required
from datetime import date
from app import db
from app.forms import HeaderForm, FileUploadForm # Added FileUploadForm
from app.schemas.saft_data import Header as HeaderPydanticModel, AddressStructure as AddressPydanticModel
from app.models.saft_models import SaftHeaderData
import os
from werkzeug.utils import secure_filename
import pandas as pd
from flask import current_app

data_input_bp = Blueprint('data_input', __name__, url_prefix='/input')

@data_input_bp.route('/header', methods=['GET', 'POST'])
@login_required # Protect this route
def header_input():
    form = HeaderForm()

    if form.validate_on_submit():
        try:
            # Pydantic validation remains useful before DB commit
            company_address_dict = {
                'BuildingNumber': form.CompanyAddress_BuildingNumber.data if form.CompanyAddress_BuildingNumber.data else None,
                'StreetName': form.CompanyAddress_StreetName.data if form.CompanyAddress_StreetName.data else None,
                'AddressDetail': form.CompanyAddress_AddressDetail.data,
                'City': form.CompanyAddress_City.data,
                'PostalCode': form.CompanyAddress_PostalCode.data,
                'Region': form.CompanyAddress_Region.data if form.CompanyAddress_Region.data else None,
                'Country': form.CompanyAddress_Country.data
            }
            # This Pydantic instance is for validation, not directly saved
            validated_company_address = AddressPydanticModel(**company_address_dict)

            header_pydantic_data = {
                "AuditFileVersion": form.AuditFileVersion.data,
                "CompanyID": form.CompanyID.data,
                "TaxRegistrationNumber": form.TaxRegistrationNumber.data,
                "TaxAccountingBasis": form.TaxAccountingBasis.data,
                "CompanyName": form.CompanyName.data,
                "BusinessName": form.BusinessName.data if form.BusinessName.data else None,
                "CompanyAddress": validated_company_address, # Use the validated Pydantic model
                "FiscalYear": form.FiscalYear.data,
                "StartDate": form.StartDate.data,
                "EndDate": form.EndDate.data,
                "CurrencyCode": form.CurrencyCode.data,
                "DateCreated": form.DateCreated.data,
                "TaxEntity": form.TaxEntity.data,
                "ProductCompanyTaxID": form.ProductCompanyTaxID.data,
                "SoftwareCertificateNumber": form.SoftwareCertificateNumber.data,
                "ProductID": form.ProductID.data,
                "ProductVersion": form.ProductVersion.data,
                "HeaderComment": form.HeaderComment.data if form.HeaderComment.data else None,
                "Telephone": form.Telephone.data if form.Telephone.data else None,
                "Fax": form.Fax.data if form.Fax.data else None,
                "Email": form.Email.data if form.Email.data else None,
                "Website": form.Website.data if form.Website.data else None,
            }
            # This Pydantic instance is for validation
            validated_header_data = HeaderPydanticModel(**header_pydantic_data)

            # Now interact with the database model SaftHeaderData
            header_db_entry = SaftHeaderData.query.filter_by(user_id=current_user.id).order_by(SaftHeaderData.updated_at.desc()).first()

            if header_db_entry is None:
                header_db_entry = SaftHeaderData(user_id=current_user.id)
                db.session.add(header_db_entry)

            # Populate db_entry from validated_header_data (Pydantic model)
            header_db_entry.audit_file_version = validated_header_data.AuditFileVersion
            header_db_entry.company_id = validated_header_data.CompanyID
            header_db_entry.tax_registration_number = validated_header_data.TaxRegistrationNumber
            header_db_entry.tax_accounting_basis = validated_header_data.TaxAccountingBasis # Enum value
            header_db_entry.company_name = validated_header_data.CompanyName
            header_db_entry.business_name = validated_header_data.BusinessName

            # Populate address fields from the validated_company_address Pydantic model
            header_db_entry.company_address_building_number = validated_company_address.BuildingNumber
            header_db_entry.company_address_street_name = validated_company_address.StreetName
            header_db_entry.company_address_address_detail = validated_company_address.AddressDetail
            header_db_entry.company_address_city = validated_company_address.City
            header_db_entry.company_address_postal_code = validated_company_address.PostalCode
            header_db_entry.company_address_region = validated_company_address.Region
            header_db_entry.company_address_country = validated_company_address.Country

            header_db_entry.fiscal_year = validated_header_data.FiscalYear
            header_db_entry.start_date = validated_header_data.StartDate
            header_db_entry.end_date = validated_header_data.EndDate
            header_db_entry.currency_code = validated_header_data.CurrencyCode # Enum value
            header_db_entry.date_created = validated_header_data.DateCreated
            header_db_entry.tax_entity = validated_header_data.TaxEntity
            header_db_entry.product_company_tax_id = validated_header_data.ProductCompanyTaxID
            header_db_entry.software_certificate_number = validated_header_data.SoftwareCertificateNumber
            header_db_entry.product_id = validated_header_data.ProductID
            header_db_entry.product_version = validated_header_data.ProductVersion
            header_db_entry.header_comment = validated_header_data.HeaderComment
            header_db_entry.telephone = validated_header_data.Telephone
            header_db_entry.fax = validated_header_data.Fax
            header_db_entry.email = validated_header_data.Email # Pydantic EmailStr converts to str
            header_db_entry.website = validated_header_data.Website

            db.session.commit()
            flash('Header data saved to database successfully!', 'success')
            return redirect(url_for('data_input.header_input'))

        except Exception as e: # Catch Pydantic validation errors or DB errors
            db.session.rollback() # Rollback in case of DB error during commit
            flash(f'Error saving header data: {str(e)}', 'danger')

    elif request.method == 'GET':
        header_db_entry = SaftHeaderData.query.filter_by(user_id=current_user.id).order_by(SaftHeaderData.updated_at.desc()).first()
        if header_db_entry:
            # Populate form from DB entry
            form.AuditFileVersion.data = header_db_entry.audit_file_version
            form.CompanyID.data = header_db_entry.company_id
            form.TaxRegistrationNumber.data = header_db_entry.tax_registration_number
            form.TaxAccountingBasis.data = header_db_entry.tax_accounting_basis.value # Get enum value for form
            form.CompanyName.data = header_db_entry.company_name
            form.BusinessName.data = header_db_entry.business_name

            form.CompanyAddress_BuildingNumber.data = header_db_entry.company_address_building_number
            form.CompanyAddress_StreetName.data = header_db_entry.company_address_street_name
            form.CompanyAddress_AddressDetail.data = header_db_entry.company_address_address_detail
            form.CompanyAddress_City.data = header_db_entry.company_address_city
            form.CompanyAddress_PostalCode.data = header_db_entry.company_address_postal_code
            form.CompanyAddress_Region.data = header_db_entry.company_address_region
            form.CompanyAddress_Country.data = header_db_entry.company_address_country

            form.FiscalYear.data = header_db_entry.fiscal_year
            form.StartDate.data = header_db_entry.start_date
            form.EndDate.data = header_db_entry.end_date
            form.CurrencyCode.data = header_db_entry.currency_code.value # Get enum value for form
            form.DateCreated.data = header_db_entry.date_created
            form.TaxEntity.data = header_db_entry.tax_entity
            form.ProductCompanyTaxID.data = header_db_entry.product_company_tax_id
            form.SoftwareCertificateNumber.data = header_db_entry.software_certificate_number
            form.ProductID.data = header_db_entry.product_id
            form.ProductVersion.data = header_db_entry.product_version
            form.HeaderComment.data = header_db_entry.header_comment
            form.Telephone.data = header_db_entry.telephone
            form.Fax.data = header_db_entry.fax
            form.Email.data = header_db_entry.email
            form.Website.data = header_db_entry.website
        else:
            flash('No header data found in database. Please enter new data.', 'info')

    return render_template('data_input/header_form.html', form=form, title="SAF-T Header Input")


@data_input_bp.route('/upload/transactions', methods=['GET', 'POST'])
@login_required
def upload_transaction_file():
    form = FileUploadForm()
    upload_feedback = None # To store feedback about the uploaded file

    if form.validate_on_submit():
        file = form.data_file.data
        filename = secure_filename(file.filename)

        user_upload_dir = os.path.join(current_app.instance_path, 'uploads', str(current_user.id))
        if not os.path.exists(user_upload_dir):
            os.makedirs(user_upload_dir)

        file_path = os.path.join(user_upload_dir, filename)

        try:
            file.save(file_path)

            if filename.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=5)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file_path, nrows=5, engine='openpyxl')
            else:
                flash('Unsupported file type somehow bypassed form validation.', 'danger')
                return render_template('data_input/upload_form.html', form=form, title="Upload Transaction Data", upload_feedback=None)

            headers = df.columns.tolist()
            sample_data = df.head().to_html(classes=['table', 'table-striped', 'table-sm'], index=False, border=0)
            row_count = len(df)

            upload_feedback = {
                'filename': filename,
                'path': file_path,
                'headers': headers,
                'sample_data_html': sample_data,
                'row_count_sample': row_count,
                'message': f"File '{filename}' uploaded successfully. Headers and sample data shown below."
            }

            session['uploaded_file_info'] = {
                'filepath': file_path,
                'original_filename': filename,
                'headers': headers,
            }
            flash(upload_feedback['message'], 'success')

        except Exception as e:
            # Log the full error and traceback for server-side debugging
            current_app.logger.error(f"Error processing uploaded file '{filename}': {e}", exc_info=True)

            # Flash a more user-friendly, generic error message
            user_error_message = "An unexpected error occurred while processing your file. Please ensure it is a valid CSV or Excel file and try again. If the problem persists, contact support."
            flash(user_error_message, 'danger')
            upload_feedback = {'error': user_error_message} # Also update feedback for template display

    return render_template('data_input/upload_form.html', form=form, title="Upload Transaction Data", upload_feedback=upload_feedback)
