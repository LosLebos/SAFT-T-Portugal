from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app import db
from app.models.saft_models import MappingProfile, FieldMapping
from app.forms import CreateMappingProfileForm, EditMappingsForm
from app.mapping_fields import get_mappable_fields

mapping_bp = Blueprint('mapping', __name__, url_prefix='/mapping')

def populate_mapping_entry_choices(form_entry_field):
    # form_entry_field is a FieldMappingEntryForm instance's form attribute
    mappable_fields_choices = [(f, f) for f in get_mappable_fields()]
    form_entry_field.saft_internal_field.choices = mappable_fields_choices

@mapping_bp.route('/profiles')
@login_required
def list_profiles():
    profiles = MappingProfile.query.filter_by(user_id=current_user.id).order_by(MappingProfile.name).all()
    return render_template('mapping/profile_list.html', profiles=profiles, title="Mapping Profiles")

@mapping_bp.route('/profiles/create', methods=['GET', 'POST'])
@login_required
def create_profile():
    form = CreateMappingProfileForm()
    if form.validate_on_submit():
        existing_profile = MappingProfile.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if existing_profile:
            flash('A profile with this name already exists.', 'warning')
        else:
            profile = MappingProfile(
                name=form.name.data,
                description=form.description.data,
                user_id=current_user.id
            )
            db.session.add(profile)
            db.session.commit()
            flash('Mapping profile created successfully. You can now add field mappings.', 'success')
            return redirect(url_for('mapping.edit_profile_mappings', profile_id=profile.id))
    return render_template('mapping/profile_form.html', form=form, title="Create Mapping Profile")

@mapping_bp.route('/profiles/<int:profile_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile_mappings(profile_id):
    profile = MappingProfile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        flash('You are not authorized to edit this profile.', 'danger')
        return redirect(url_for('mapping.list_profiles'))

    form = EditMappingsForm(request.form if request.method == 'POST' else None, obj=profile)

    # Special handling for 'Add Another Mapping' button if it's a separate submit button
    # This assumes 'add_mapping_row_button' is the name of that specific submit button
    if 'add_mapping_row_button' in request.form: # Check if the add_mapping_row button was pressed
        form.mappings.append_entry()
        # Choices will be populated for all rows before rendering.
        # We don't validate or save, just re-render with an extra row.
    elif form.validate_on_submit(): # Process main form submission
        try:
            profile.name = form.name.data
            profile.description = form.description.data

            # Simple strategy: delete existing and re-add all from form
            FieldMapping.query.filter_by(profile_id=profile.id).delete()
            # db.session.flush() # Optional

            for mapping_entry_data in form.mappings.data: # form.mappings.data gives a list of dicts
                if mapping_entry_data['saft_internal_field'] and mapping_entry_data['source_column_name']:
                    field_map = FieldMapping(
                        profile_id=profile.id,
                        saft_internal_field=mapping_entry_data['saft_internal_field'],
                        source_column_name=mapping_entry_data['source_column_name'],
                        default_value=mapping_entry_data.get('default_value')
                    )
                    db.session.add(field_map)

            db.session.commit()
            flash('Mapping profile updated successfully.', 'success')
            return redirect(url_for('mapping.edit_profile_mappings', profile_id=profile.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')

    # Populate form.mappings from DB for GET requests
    if request.method == 'GET':
        # Clear existing entries that might have been added by min_entries or obj=profile
        while len(form.mappings.entries) > 0:
            form.mappings.pop_entry()

        db_mappings = profile.field_mappings.order_by(FieldMapping.id).all()
        for db_mapping in db_mappings:
            form.mappings.append_entry(data={
                'saft_internal_field': db_mapping.saft_internal_field,
                'source_column_name': db_mapping.source_column_name,
                'default_value': db_mapping.default_value
            })

    # Ensure at least min_entries are present for rendering if form is new or all entries were removed
    # This is primarily for GET requests for new/empty profiles.
    # For POST with add_mapping_row, append_entry was already called.
    # For POST with submit, if validation fails, we want to show submitted data, not min_entries.
    if request.method == 'GET' and not profile.field_mappings.first(): # If no mappings in DB
        needed_entries = form.mappings.min_entries - len(form.mappings.entries)
        for _ in range(max(0, needed_entries)): # Ensure it's not negative
             form.mappings.append_entry()


    # Populate choices for all saft_internal_field SelectFields in the FieldList
    # This needs to be done on every request path that leads to rendering the form
    for mapping_entry_fieldlist_item_proxy in form.mappings:
        # mapping_entry_fieldlist_item_proxy is an UnboundField/FormField object.
        # We need to access its .form attribute which is the actual FieldMappingEntryForm instance.
        populate_mapping_entry_choices(mapping_entry_fieldlist_item_proxy.form)

    return render_template('mapping/edit_mappings.html', form=form, profile=profile, title=f"Edit Mappings for {profile.name}")

@mapping_bp.route('/profiles/<int:profile_id>/delete', methods=['POST'])
@login_required
def delete_profile(profile_id):
    profile = MappingProfile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        flash('You are not authorized to delete this profile.', 'danger')
        return redirect(url_for('mapping.list_profiles'))
    try:
        db.session.delete(profile)
        db.session.commit()
        flash('Mapping profile deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting profile: {str(e)}', 'danger')
    return redirect(url_for('mapping.list_profiles'))

@mapping_bp.route('/profiles/<int:profile_id>/set_active', methods=['POST'])
@login_required
def set_active_profile(profile_id):
    profile_to_activate = MappingProfile.query.get_or_404(profile_id)

    if profile_to_activate.user_id != current_user.id:
        flash('You are not authorized to modify this profile.', 'danger')
        return redirect(url_for('mapping.list_profiles'))

    try:
        # Set all other profiles for this user to inactive
        MappingProfile.query.filter_by(user_id=current_user.id).update({'is_active': False})

        # Activate the selected profile
        profile_to_activate.is_active = True

        db.session.commit()
        flash(f'Profile "{profile_to_activate.name}" is now active.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting active profile: {str(e)}', 'danger')

    return redirect(url_for('mapping.list_profiles'))
