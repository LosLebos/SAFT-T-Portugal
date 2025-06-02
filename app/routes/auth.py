from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User # Assuming user.py is in app/models/
# Assuming HeaderForm is in app.forms, not directly used here but for context
# from app.forms import LoginForm, RegistrationForm # If you create separate forms

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Using HeaderForm for now for username/password, ideally create specific Login/Register forms.
# For simplicity, this subtask will adapt the existing template expectations.
# A later step could be to create dedicated LoginForm and RegistrationForm.

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # This route expects 'username' and 'password' from a generic form.
    # If using WTForms, you'd instantiate a registration form here.
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email') # Assuming email field is added to form

        if not username or not password or not email:
            flash('Username, email, and password are required.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'warning')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'warning')
            return redirect(url_for('auth.register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    # For GET, it will render the template which should have username, email, password fields.
    return render_template('auth/register.html') # Ensure this template has an email field

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username') # Or email, if allowing login with email
        password = request.form.get('password')

        if not username or not password:
            flash('Username/Email and password are required.', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(username=username).first()
        # Optionally, allow login with email:
        # if not user:
        #    user = User.query.filter_by(email=username).first()

        if user is None or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=request.form.get('remember_me')) # Add remember_me if form has it
        flash('Login successful!', 'success')

        # Redirect to next page if available, otherwise to index
        next_page = request.args.get('next')
        if not next_page or url_for(next_page).host != request.host: # Security: check host
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html') # Ensure this template is compatible

@auth_bp.route('/logout')
@login_required # Ensure user is logged in to log out
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
