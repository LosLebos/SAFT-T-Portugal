from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required
from app import db
from app.models.saft_models import CustomerDb, SupplierDb, ProductDb, GeneralLedgerAccountDb # Added GeneralLedgerAccountDb
from app.forms import CustomerForm, SupplierForm, ProductForm, GLAccountForm # Added GLAccountForm
from app.schemas.saft_data import Customer as CustomerPydantic, \
                                 Supplier as SupplierPydantic, \
                                 Product as ProductPydantic, \
                                 GeneralLedgerAccount as GLAccountPydantic, \
                                 CustomerAddressStructure as CustomerAddressPydantic, \
                                 AddressStructure as AddressPydantic
from pydantic import ValidationError

masterfiles_bp = Blueprint('masterfiles', __name__, url_prefix='/masterfiles')

# --- Customer Helper Functions and Routes ---
def _populate_customer_db_from_pydantic(customer_db_instance: CustomerDb, pydantic_instance: CustomerPydantic):
    customer_db_instance.customer_id_field = pydantic_instance.CustomerID
    customer_db_instance.account_id = pydantic_instance.AccountID
    customer_db_instance.customer_tax_id = pydantic_instance.CustomerTaxID
    customer_db_instance.company_name = pydantic_instance.CompanyName
    customer_db_instance.contact = pydantic_instance.Contact

    if pydantic_instance.BillingAddress:
        customer_db_instance.billing_address_building_number = pydantic_instance.BillingAddress.BuildingNumber
        customer_db_instance.billing_address_street_name = pydantic_instance.BillingAddress.StreetName
        customer_db_instance.billing_address_address_detail = pydantic_instance.BillingAddress.AddressDetail
        customer_db_instance.billing_address_city = pydantic_instance.BillingAddress.City
        customer_db_instance.billing_address_postal_code = pydantic_instance.BillingAddress.PostalCode
        customer_db_instance.billing_address_region = pydantic_instance.BillingAddress.Region
        customer_db_instance.billing_address_country = pydantic_instance.BillingAddress.Country

    if pydantic_instance.ShipToAddress and len(pydantic_instance.ShipToAddress) > 0:
        shipping_addr_pydantic = pydantic_instance.ShipToAddress[0]
        customer_db_instance.shipping_address_building_number = shipping_addr_pydantic.BuildingNumber
        customer_db_instance.shipping_address_street_name = shipping_addr_pydantic.StreetName
        customer_db_instance.shipping_address_address_detail = shipping_addr_pydantic.AddressDetail
        customer_db_instance.shipping_address_city = shipping_addr_pydantic.City
        customer_db_instance.shipping_address_postal_code = shipping_addr_pydantic.PostalCode
        customer_db_instance.shipping_address_region = shipping_addr_pydantic.Region
        customer_db_instance.shipping_address_country = shipping_addr_pydantic.Country
    else:
        customer_db_instance.shipping_address_building_number = None
        customer_db_instance.shipping_address_street_name = None
        customer_db_instance.shipping_address_address_detail = None
        customer_db_instance.shipping_address_city = None
        customer_db_instance.shipping_address_postal_code = None
        customer_db_instance.shipping_address_region = None
        customer_db_instance.shipping_address_country = None

    customer_db_instance.telephone = pydantic_instance.Telephone
    customer_db_instance.fax = pydantic_instance.Fax
    customer_db_instance.email = str(pydantic_instance.Email) if pydantic_instance.Email else None
    customer_db_instance.website = pydantic_instance.Website
    customer_db_instance.self_billing_indicator = pydantic_instance.SelfBillingIndicator

def _populate_form_from_db(form: CustomerForm, customer_db_entry: CustomerDb): # Specific to CustomerForm
    form.customer_id_field.data = customer_db_entry.customer_id_field
    form.account_id.data = customer_db_entry.account_id
    form.customer_tax_id.data = customer_db_entry.customer_tax_id
    form.company_name.data = customer_db_entry.company_name
    form.contact.data = customer_db_entry.contact

    if form.billing_address.form:
        form.billing_address.form.BuildingNumber.data = customer_db_entry.billing_address_building_number
        form.billing_address.form.StreetName.data = customer_db_entry.billing_address_street_name
        form.billing_address.form.AddressDetail.data = customer_db_entry.billing_address_address_detail
        form.billing_address.form.City.data = customer_db_entry.billing_address_city
        form.billing_address.form.PostalCode.data = customer_db_entry.billing_address_postal_code
        form.billing_address.form.Region.data = customer_db_entry.billing_address_region
        form.billing_address.form.Country.data = customer_db_entry.billing_address_country

    if form.shipping_address.form:
        form.shipping_address.form.BuildingNumber.data = customer_db_entry.shipping_address_building_number
        form.shipping_address.form.StreetName.data = customer_db_entry.shipping_address_street_name
        form.shipping_address.form.AddressDetail.data = customer_db_entry.shipping_address_address_detail
        form.shipping_address.form.City.data = customer_db_entry.shipping_address_city
        form.shipping_address.form.PostalCode.data = customer_db_entry.shipping_address_postal_code
        form.shipping_address.form.Region.data = customer_db_entry.shipping_address_region
        form.shipping_address.form.Country.data = customer_db_entry.shipping_address_country

    form.telephone.data = customer_db_entry.telephone
    form.fax.data = customer_db_entry.fax
    form.email.data = customer_db_entry.email
    form.website.data = customer_db_entry.website
    form.self_billing_indicator.data = customer_db_entry.self_billing_indicator

@masterfiles_bp.route('/customers')
@login_required
def list_customers():
    customers = CustomerDb.query.filter_by(user_id=current_user.id).order_by(CustomerDb.company_name).all()
    return render_template('masterfiles/customer_list.html', customers=customers, title="Manage Customers")

@masterfiles_bp.route('/customer/create', methods=['GET', 'POST'])
@login_required
def create_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            billing_address_pydantic = CustomerAddressPydantic(**form.billing_address.data)

            shipping_address_pydantic_list = []
            shipping_data = form.shipping_address.data
            if shipping_data and shipping_data.get('AddressDetail') and shipping_data.get('City') and shipping_data.get('PostalCode') and shipping_data.get('Country'):
                shipping_address_pydantic_list.append(CustomerAddressPydantic(**shipping_data))

            customer_pydantic_data = {
                "CustomerID": form.customer_id_field.data, "AccountID": form.account_id.data,
                "CustomerTaxID": form.customer_tax_id.data, "CompanyName": form.company_name.data,
                "Contact": form.contact.data, "BillingAddress": billing_address_pydantic,
                "ShipToAddress": shipping_address_pydantic_list if shipping_address_pydantic_list else None,
                "Telephone": form.telephone.data, "Fax": form.fax.data,
                "Email": form.email.data if form.email.data else None,
                "Website": form.website.data, "SelfBillingIndicator": form.self_billing_indicator.data
            }
            validated_customer_pydantic = CustomerPydantic(**customer_pydantic_data)

            existing_customer = CustomerDb.query.filter_by(user_id=current_user.id, customer_id_field=validated_customer_pydantic.CustomerID).first()
            if existing_customer:
                flash('A customer with this Customer ID already exists for your account.', 'warning')
            else:
                new_customer_db = CustomerDb(user_id=current_user.id)
                _populate_customer_db_from_pydantic(new_customer_db, validated_customer_pydantic)
                db.session.add(new_customer_db)
                db.session.commit()
                flash('Customer created successfully.', 'success')
                return redirect(url_for('masterfiles.list_customers'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating customer: {e}", exc_info=True)
            flash('An unexpected error occurred while creating the customer.', 'danger')

    return render_template('masterfiles/customer_form.html', form=form, title="Create New Customer", action_text="Create")

@masterfiles_bp.route('/customer/<int:customer_db_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_db_id):
    customer_db_entry = CustomerDb.query.get_or_404(customer_db_id)
    if customer_db_entry.user_id != current_user.id:
        flash('You are not authorized to edit this customer.', 'danger')
        return redirect(url_for('masterfiles.list_customers'))

    form = CustomerForm(obj=customer_db_entry if request.method == 'GET' else None)
    if request.method == 'GET':
        _populate_form_from_db(form, customer_db_entry)

    if form.validate_on_submit():
        try:
            billing_address_pydantic = CustomerAddressPydantic(**form.billing_address.data)
            shipping_address_pydantic_list = []
            shipping_data = form.shipping_address.data
            if shipping_data and shipping_data.get('AddressDetail') and shipping_data.get('City') and shipping_data.get('PostalCode') and shipping_data.get('Country'):
                shipping_address_pydantic_list.append(CustomerAddressPydantic(**shipping_data))

            customer_pydantic_data = {
                "CustomerID": form.customer_id_field.data, "AccountID": form.account_id.data,
                "CustomerTaxID": form.customer_tax_id.data, "CompanyName": form.company_name.data,
                "Contact": form.contact.data, "BillingAddress": billing_address_pydantic,
                "ShipToAddress": shipping_address_pydantic_list if shipping_address_pydantic_list else None,
                "Telephone": form.telephone.data, "Fax": form.fax.data,
                "Email": form.email.data if form.email.data else None,
                "Website": form.website.data, "SelfBillingIndicator": form.self_billing_indicator.data
            }
            validated_customer_pydantic = CustomerPydantic(**customer_pydantic_data)

            if customer_db_entry.customer_id_field != validated_customer_pydantic.CustomerID:
                existing_customer_check = CustomerDb.query.filter_by(user_id=current_user.id, customer_id_field=validated_customer_pydantic.CustomerID).first()
                if existing_customer_check and existing_customer_check.id != customer_db_entry.id:
                    flash('Another customer with this Customer ID already exists for your account.', 'warning')
                    return render_template('masterfiles/customer_form.html', form=form, title="Edit Customer", action_text="Update", customer_db_id=customer_db_id)

            _populate_customer_db_from_pydantic(customer_db_entry, validated_customer_pydantic)
            db.session.commit()
            flash('Customer updated successfully.', 'success')
            return redirect(url_for('masterfiles.list_customers'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating customer: {e}", exc_info=True)
            flash('An unexpected error occurred while updating the customer.', 'danger')

    return render_template('masterfiles/customer_form.html', form=form, title="Edit Customer", action_text="Update", customer_db_id=customer_db_id)

@masterfiles_bp.route('/customer/<int:customer_db_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_db_id):
    customer = CustomerDb.query.get_or_404(customer_db_id)
    if customer.user_id != current_user.id:
        flash('You are not authorized to delete this customer.', 'danger')
    else:
        try:
            db.session.delete(customer)
            db.session.commit()
            flash('Customer deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting customer: {e}", exc_info=True)
            flash('An error occurred while deleting the customer.', 'danger')
    return redirect(url_for('masterfiles.list_customers'))

# --- Supplier Helper Functions and Routes ---
def _populate_supplier_db_from_pydantic(supplier_db_instance: SupplierDb, pydantic_instance: SupplierPydantic):
    supplier_db_instance.supplier_id_field = pydantic_instance.SupplierID
    supplier_db_instance.account_id = pydantic_instance.AccountID
    supplier_db_instance.supplier_tax_id = pydantic_instance.SupplierTaxID
    supplier_db_instance.company_name = pydantic_instance.CompanyName
    supplier_db_instance.contact = pydantic_instance.Contact
    if pydantic_instance.BillingAddress:
        supplier_db_instance.billing_address_building_number = pydantic_instance.BillingAddress.BuildingNumber
        supplier_db_instance.billing_address_street_name = pydantic_instance.BillingAddress.StreetName
        supplier_db_instance.billing_address_address_detail = pydantic_instance.BillingAddress.AddressDetail
        supplier_db_instance.billing_address_city = pydantic_instance.BillingAddress.City
        supplier_db_instance.billing_address_postal_code = pydantic_instance.BillingAddress.PostalCode
        supplier_db_instance.billing_address_region = pydantic_instance.BillingAddress.Region
        supplier_db_instance.billing_address_country = pydantic_instance.BillingAddress.Country
    if pydantic_instance.ShipFromAddress and len(pydantic_instance.ShipFromAddress) > 0:
        shipping_addr_pydantic = pydantic_instance.ShipFromAddress[0]
        supplier_db_instance.ship_from_address_building_number = shipping_addr_pydantic.BuildingNumber
        supplier_db_instance.ship_from_address_street_name = shipping_addr_pydantic.StreetName
        supplier_db_instance.ship_from_address_address_detail = shipping_addr_pydantic.AddressDetail
        supplier_db_instance.ship_from_address_city = shipping_addr_pydantic.City
        supplier_db_instance.ship_from_address_postal_code = shipping_addr_pydantic.PostalCode
        supplier_db_instance.ship_from_address_region = shipping_addr_pydantic.Region
        supplier_db_instance.ship_from_address_country = shipping_addr_pydantic.Country
    else:
        supplier_db_instance.ship_from_address_building_number = None
        supplier_db_instance.ship_from_address_street_name = None
        supplier_db_instance.ship_from_address_address_detail = None
        supplier_db_instance.ship_from_address_city = None
        supplier_db_instance.ship_from_address_postal_code = None
        supplier_db_instance.ship_from_address_region = None
        supplier_db_instance.ship_from_address_country = None
    supplier_db_instance.telephone = pydantic_instance.Telephone
    supplier_db_instance.fax = pydantic_instance.Fax
    supplier_db_instance.email = str(pydantic_instance.Email) if pydantic_instance.Email else None
    supplier_db_instance.website = pydantic_instance.Website
    supplier_db_instance.self_billing_indicator = pydantic_instance.SelfBillingIndicator

def _populate_supplier_form_from_db(form: SupplierForm, supplier_db_entry: SupplierDb):
    form.supplier_id_field.data = supplier_db_entry.supplier_id_field
    form.account_id.data = supplier_db_entry.account_id
    form.supplier_tax_id.data = supplier_db_entry.supplier_tax_id
    form.company_name.data = supplier_db_entry.company_name
    form.contact.data = supplier_db_entry.contact
    if form.billing_address.form:
        form.billing_address.form.BuildingNumber.data = supplier_db_entry.billing_address_building_number
        form.billing_address.form.StreetName.data = supplier_db_entry.billing_address_street_name
        form.billing_address.form.AddressDetail.data = supplier_db_entry.billing_address_address_detail
        form.billing_address.form.City.data = supplier_db_entry.billing_address_city
        form.billing_address.form.PostalCode.data = supplier_db_entry.billing_address_postal_code
        form.billing_address.form.Region.data = supplier_db_entry.billing_address_region
        form.billing_address.form.Country.data = supplier_db_entry.billing_address_country
    if form.ship_from_address.form:
        form.ship_from_address.form.BuildingNumber.data = supplier_db_entry.ship_from_address_building_number
        form.ship_from_address.form.StreetName.data = supplier_db_entry.ship_from_address_street_name
        form.ship_from_address.form.AddressDetail.data = supplier_db_entry.ship_from_address_address_detail
        form.ship_from_address.form.City.data = supplier_db_entry.ship_from_address_city
        form.ship_from_address.form.PostalCode.data = supplier_db_entry.ship_from_address_postal_code
        form.ship_from_address.form.Region.data = supplier_db_entry.ship_from_address_region
        form.ship_from_address.form.Country.data = supplier_db_entry.ship_from_address_country
    form.telephone.data = supplier_db_entry.telephone
    form.fax.data = supplier_db_entry.fax
    form.email.data = supplier_db_entry.email
    form.website.data = supplier_db_entry.website
    form.self_billing_indicator.data = supplier_db_entry.self_billing_indicator

@masterfiles_bp.route('/suppliers')
@login_required
def list_suppliers():
    suppliers = SupplierDb.query.filter_by(user_id=current_user.id).order_by(SupplierDb.company_name).all()
    return render_template('masterfiles/supplier_list.html', suppliers=suppliers, title="Manage Suppliers")

@masterfiles_bp.route('/supplier/create', methods=['GET', 'POST'])
@login_required
def create_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        try:
            billing_address_pydantic = AddressPydantic(**form.billing_address.data)
            ship_from_address_pydantic_list = []
            ship_from_data = form.ship_from_address.data
            if ship_from_data and ship_from_data.get('AddressDetail') and ship_from_data.get('City') and ship_from_data.get('PostalCode') and ship_from_data.get('Country'):
                ship_from_address_pydantic_list.append(AddressPydantic(**ship_from_data))

            supplier_pydantic_data = {
                "SupplierID": form.supplier_id_field.data, "AccountID": form.account_id.data,
                "SupplierTaxID": form.supplier_tax_id.data, "CompanyName": form.company_name.data,
                "Contact": form.contact.data, "BillingAddress": billing_address_pydantic,
                "ShipFromAddress": ship_from_address_pydantic_list if ship_from_address_pydantic_list else None,
                "Telephone": form.telephone.data, "Fax": form.fax.data,
                "Email": form.email.data if form.email.data else None,
                "Website": form.website.data, "SelfBillingIndicator": form.self_billing_indicator.data
            }
            validated_supplier_pydantic = SupplierPydantic(**supplier_pydantic_data)

            existing_supplier = SupplierDb.query.filter_by(user_id=current_user.id, supplier_id_field=validated_supplier_pydantic.SupplierID).first()
            if existing_supplier:
                flash('A supplier with this Supplier ID already exists for your account.', 'warning')
            else:
                new_supplier_db = SupplierDb(user_id=current_user.id)
                _populate_supplier_db_from_pydantic(new_supplier_db, validated_supplier_pydantic)
                db.session.add(new_supplier_db)
                db.session.commit()
                flash('Supplier created successfully.', 'success')
                return redirect(url_for('masterfiles.list_suppliers'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating supplier: {e}", exc_info=True)
            flash('An unexpected error occurred while creating the supplier.', 'danger')

    return render_template('masterfiles/supplier_form.html', form=form, title="Create New Supplier", action_text="Create")

@masterfiles_bp.route('/supplier/<int:supplier_db_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(supplier_db_id):
    supplier_db_entry = SupplierDb.query.get_or_404(supplier_db_id)
    if supplier_db_entry.user_id != current_user.id:
        flash('You are not authorized to edit this supplier.', 'danger')
        return redirect(url_for('masterfiles.list_suppliers'))

    form = SupplierForm(obj=supplier_db_entry if request.method == 'GET' else None)
    if request.method == 'GET':
        _populate_supplier_form_from_db(form, supplier_db_entry)

    if form.validate_on_submit():
        try:
            billing_address_pydantic = AddressPydantic(**form.billing_address.data)
            ship_from_address_pydantic_list = []
            ship_from_data = form.ship_from_address.data
            if ship_from_data and ship_from_data.get('AddressDetail') and ship_from_data.get('City') and ship_from_data.get('PostalCode') and ship_from_data.get('Country'):
                ship_from_address_pydantic_list.append(AddressPydantic(**ship_from_data))

            supplier_pydantic_data = {
                "SupplierID": form.supplier_id_field.data, "AccountID": form.account_id.data,
                "SupplierTaxID": form.supplier_tax_id.data, "CompanyName": form.company_name.data,
                "Contact": form.contact.data, "BillingAddress": billing_address_pydantic,
                "ShipFromAddress": ship_from_address_pydantic_list if ship_from_address_pydantic_list else None,
                "Telephone": form.telephone.data, "Fax": form.fax.data,
                "Email": form.email.data if form.email.data else None,
                "Website": form.website.data, "SelfBillingIndicator": form.self_billing_indicator.data
            }
            validated_supplier_pydantic = SupplierPydantic(**supplier_pydantic_data)

            if supplier_db_entry.supplier_id_field != validated_supplier_pydantic.SupplierID:
                existing_supplier_check = SupplierDb.query.filter_by(user_id=current_user.id, supplier_id_field=validated_supplier_pydantic.SupplierID).first()
                if existing_supplier_check and existing_supplier_check.id != supplier_db_entry.id:
                    flash('Another supplier with this Supplier ID already exists for your account.', 'warning')
                    return render_template('masterfiles/supplier_form.html', form=form, title="Edit Supplier", action_text="Update", supplier_db_id=supplier_db_id)

            _populate_supplier_db_from_pydantic(supplier_db_entry, validated_supplier_pydantic)
            db.session.commit()
            flash('Supplier updated successfully.', 'success')
            return redirect(url_for('masterfiles.list_suppliers'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating supplier: {e}", exc_info=True)
            flash('An unexpected error occurred while updating the supplier.', 'danger')

    return render_template('masterfiles/supplier_form.html', form=form, title="Edit Supplier", action_text="Update", supplier_db_id=supplier_db_id)

@masterfiles_bp.route('/supplier/<int:supplier_db_id>/delete', methods=['POST'])
@login_required
def delete_supplier(supplier_db_id):
    supplier = SupplierDb.query.get_or_404(supplier_db_id)
    if supplier.user_id != current_user.id:
        flash('You are not authorized to delete this supplier.', 'danger')
    else:
        try:
            db.session.delete(supplier)
            db.session.commit()
            flash('Supplier deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting supplier: {e}", exc_info=True)
            flash('An error occurred while deleting the supplier.', 'danger')
    return redirect(url_for('masterfiles.list_suppliers'))

# --- Product Helper Functions and Routes ---

def _populate_product_db_from_pydantic(product_db_instance: ProductDb, pydantic_instance: ProductPydantic):
    product_db_instance.product_type = pydantic_instance.ProductType
    product_db_instance.product_code = pydantic_instance.ProductCode
    product_db_instance.product_group = pydantic_instance.ProductGroup
    product_db_instance.product_description = pydantic_instance.ProductDescription
    product_db_instance.product_number_code = pydantic_instance.ProductNumberCode

def _populate_product_form_from_db(form: ProductForm, product_db_entry: ProductDb):
    form.product_type.data = product_db_entry.product_type.value
    form.product_code.data = product_db_entry.product_code
    form.product_group.data = product_db_entry.product_group
    form.product_description.data = product_db_entry.product_description
    form.product_number_code.data = product_db_entry.product_number_code

@masterfiles_bp.route('/products')
@login_required
def list_products():
    products = ProductDb.query.filter_by(user_id=current_user.id).order_by(ProductDb.product_description).all()
    return render_template('masterfiles/product_list.html', products=products, title="Manage Products")

@masterfiles_bp.route('/product/create', methods=['GET', 'POST'])
@login_required
def create_product():
    form = ProductForm()
    if form.validate_on_submit():
        try:
            product_pydantic_data = {
                "ProductType": form.product_type.data,
                "ProductCode": form.product_code.data,
                "ProductGroup": form.product_group.data,
                "ProductDescription": form.product_description.data,
                "ProductNumberCode": form.product_number_code.data
            }
            validated_product_pydantic = ProductPydantic(**product_pydantic_data)

            existing_product = ProductDb.query.filter_by(user_id=current_user.id, product_code=validated_product_pydantic.ProductCode).first()
            if existing_product:
                flash('A product with this Product Code already exists for your account.', 'warning')
            else:
                new_product_db = ProductDb(user_id=current_user.id)
                _populate_product_db_from_pydantic(new_product_db, validated_product_pydantic)
                db.session.add(new_product_db)
                db.session.commit()
                flash('Product created successfully.', 'success')
                return redirect(url_for('masterfiles.list_products'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating product: {e}", exc_info=True)
            flash('An unexpected error occurred while creating the product.', 'danger')

    return render_template('masterfiles/product_form.html', form=form, title="Create New Product", action_text="Create")

@masterfiles_bp.route('/product/<int:product_db_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_db_id):
    product_db_entry = ProductDb.query.get_or_404(product_db_id)
    if product_db_entry.user_id != current_user.id:
        flash('You are not authorized to edit this product.', 'danger')
        return redirect(url_for('masterfiles.list_products'))

    form = ProductForm(obj=product_db_entry if request.method == 'GET' else None)
    if request.method == 'GET':
        _populate_product_form_from_db(form, product_db_entry)

    if form.validate_on_submit():
        try:
            product_pydantic_data = {
                "ProductType": form.product_type.data,
                "ProductCode": form.product_code.data,
                "ProductGroup": form.product_group.data,
                "ProductDescription": form.product_description.data,
                "ProductNumberCode": form.product_number_code.data
            }
            validated_product_pydantic = ProductPydantic(**product_pydantic_data)

            if product_db_entry.product_code != validated_product_pydantic.ProductCode:
                existing_product = ProductDb.query.filter_by(user_id=current_user.id, product_code=validated_product_pydantic.ProductCode).first()
                if existing_product and existing_product.id != product_db_entry.id:
                    flash('Another product with this Product Code already exists for your account.', 'warning')
                    return render_template('masterfiles/product_form.html', form=form, title="Edit Product", action_text="Update", product_db_id=product_db_id)

            _populate_product_db_from_pydantic(product_db_entry, validated_product_pydantic)
            db.session.commit()
            flash('Product updated successfully.', 'success')
            return redirect(url_for('masterfiles.list_products'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating product: {e}", exc_info=True)
            flash('An unexpected error occurred while updating the product.', 'danger')

    return render_template('masterfiles/product_form.html', form=form, title="Edit Product", action_text="Update", product_db_id=product_db_id)

@masterfiles_bp.route('/product/<int:product_db_id>/delete', methods=['POST'])
@login_required
def delete_product(product_db_id):
    product = ProductDb.query.get_or_404(product_db_id)
    if product.user_id != current_user.id:
        flash('You are not authorized to delete this product.', 'danger')
    else:
        try:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting product: {e}", exc_info=True)
            flash('An error occurred while deleting the product.', 'danger')
    return redirect(url_for('masterfiles.list_products'))

# --- GeneralLedgerAccount Helper Functions and Routes ---

def _populate_gl_account_db_from_pydantic(gl_account_db_instance: GeneralLedgerAccountDb, pydantic_instance: GLAccountPydantic):
    gl_account_db_instance.account_id_field = pydantic_instance.AccountID
    gl_account_db_instance.account_description = pydantic_instance.AccountDescription
    gl_account_db_instance.opening_debit_balance = pydantic_instance.OpeningDebitBalance
    gl_account_db_instance.opening_credit_balance = pydantic_instance.OpeningCreditBalance
    gl_account_db_instance.closing_debit_balance = pydantic_instance.ClosingDebitBalance
    gl_account_db_instance.closing_credit_balance = pydantic_instance.ClosingCreditBalance
    gl_account_db_instance.grouping_category = pydantic_instance.GroupingCategory
    gl_account_db_instance.grouping_code = pydantic_instance.GroupingCode
    gl_account_db_instance.taxonomy_code = pydantic_instance.TaxonomyCode

def _populate_gl_account_form_from_db(form: GLAccountForm, gl_account_db_entry: GeneralLedgerAccountDb):
    form.account_id_field.data = gl_account_db_entry.account_id_field
    form.account_description.data = gl_account_db_entry.account_description
    form.opening_debit_balance.data = gl_account_db_entry.opening_debit_balance
    form.opening_credit_balance.data = gl_account_db_entry.opening_credit_balance
    form.closing_debit_balance.data = gl_account_db_entry.closing_debit_balance
    form.closing_credit_balance.data = gl_account_db_entry.closing_credit_balance
    form.grouping_category.data = gl_account_db_entry.grouping_category.value
    form.grouping_code.data = gl_account_db_entry.grouping_code
    form.taxonomy_code.data = gl_account_db_entry.taxonomy_code

@masterfiles_bp.route('/gl_accounts')
@login_required
def list_gl_accounts():
    accounts = GeneralLedgerAccountDb.query.filter_by(user_id=current_user.id).order_by(GeneralLedgerAccountDb.account_id_field).all()
    return render_template('masterfiles/gl_account_list.html', accounts=accounts, title="Manage GL Accounts")

@masterfiles_bp.route('/gl_account/create', methods=['GET', 'POST'])
@login_required
def create_gl_account():
    form = GLAccountForm()
    if form.validate_on_submit():
        try:
            gl_account_pydantic_data = {
                "AccountID": form.account_id_field.data,
                "AccountDescription": form.account_description.data,
                "OpeningDebitBalance": form.opening_debit_balance.data,
                "OpeningCreditBalance": form.opening_credit_balance.data,
                "ClosingDebitBalance": form.closing_debit_balance.data,
                "ClosingCreditBalance": form.closing_credit_balance.data,
                "GroupingCategory": form.grouping_category.data,
                "GroupingCode": form.grouping_code.data if form.grouping_code.data else None,
                "TaxonomyCode": form.taxonomy_code.data if form.taxonomy_code.data is not None else None,
            }
            validated_gl_account_pydantic = GLAccountPydantic(**gl_account_pydantic_data)

            existing_account = GeneralLedgerAccountDb.query.filter_by(user_id=current_user.id, account_id_field=validated_gl_account_pydantic.AccountID).first()
            if existing_account:
                flash('A GL account with this Account ID already exists for your account.', 'warning')
            else:
                new_gl_account_db = GeneralLedgerAccountDb(user_id=current_user.id)
                _populate_gl_account_db_from_pydantic(new_gl_account_db, validated_gl_account_pydantic)
                db.session.add(new_gl_account_db)
                db.session.commit()
                flash('GL Account created successfully.', 'success')
                return redirect(url_for('masterfiles.list_gl_accounts'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating GL account: {e}", exc_info=True)
            flash('An unexpected error occurred while creating the GL account.', 'danger')

    return render_template('masterfiles/gl_account_form.html', form=form, title="Create New GL Account", action_text="Create")

@masterfiles_bp.route('/gl_account/<int:gl_account_db_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_gl_account(gl_account_db_id):
    gl_account_db_entry = GeneralLedgerAccountDb.query.get_or_404(gl_account_db_id)
    if gl_account_db_entry.user_id != current_user.id:
        flash('You are not authorized to edit this GL account.', 'danger')
        return redirect(url_for('masterfiles.list_gl_accounts'))

    form = GLAccountForm(obj=gl_account_db_entry if request.method == 'GET' else None)
    if request.method == 'GET':
        _populate_gl_account_form_from_db(form, gl_account_db_entry)

    if form.validate_on_submit():
        try:
            gl_account_pydantic_data = {
                "AccountID": form.account_id_field.data,
                "AccountDescription": form.account_description.data,
                "OpeningDebitBalance": form.opening_debit_balance.data,
                "OpeningCreditBalance": form.opening_credit_balance.data,
                "ClosingDebitBalance": form.closing_debit_balance.data,
                "ClosingCreditBalance": form.closing_credit_balance.data,
                "GroupingCategory": form.grouping_category.data,
                "GroupingCode": form.grouping_code.data if form.grouping_code.data else None,
                "TaxonomyCode": form.taxonomy_code.data if form.taxonomy_code.data is not None else None,
            }
            validated_gl_account_pydantic = GLAccountPydantic(**gl_account_pydantic_data)

            if gl_account_db_entry.account_id_field != validated_gl_account_pydantic.AccountID:
                existing_account = GeneralLedgerAccountDb.query.filter_by(user_id=current_user.id, account_id_field=validated_gl_account_pydantic.AccountID).first()
                if existing_account and existing_account.id != gl_account_db_entry.id:
                    flash('Another GL account with this Account ID already exists for your account.', 'warning')
                    return render_template('masterfiles/gl_account_form.html', form=form, title="Edit GL Account", action_text="Update", gl_account_db_id=gl_account_db_id)

            _populate_gl_account_db_from_pydantic(gl_account_db_entry, validated_gl_account_pydantic)
            db.session.commit()
            flash('GL Account updated successfully.', 'success')
            return redirect(url_for('masterfiles.list_gl_accounts'))
        except ValidationError as e:
            error_messages = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
            flash(f"Data validation error: {'; '.join(error_messages)}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating GL account: {e}", exc_info=True)
            flash('An unexpected error occurred while updating the GL account.', 'danger')

    return render_template('masterfiles/gl_account_form.html', form=form, title="Edit GL Account", action_text="Update", gl_account_db_id=gl_account_db_id)

@masterfiles_bp.route('/gl_account/<int:gl_account_db_id>/delete', methods=['POST'])
@login_required
def delete_gl_account(gl_account_db_id):
    account = GeneralLedgerAccountDb.query.get_or_404(gl_account_db_id)
    if account.user_id != current_user.id:
        flash('You are not authorized to delete this GL account.', 'danger')
    else:
        try:
            db.session.delete(account)
            db.session.commit()
            flash('GL Account deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting GL account: {e}", exc_info=True)
            flash('An error occurred while deleting the GL account.', 'danger')
    return redirect(url_for('masterfiles.list_gl_accounts'))

