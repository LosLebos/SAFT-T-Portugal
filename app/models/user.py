from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
# Removed: SaftHeaderData import, as it's defined in saft_models.py and relationship is there

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Relationship to SaftHeaderData (defined in saft_models.py via backref 'saft_header_data_entries')
    # saft_header_data_entries is created by backref from SaftHeaderData.user

    # Relationship to MappingProfile
    mapping_profiles = db.relationship('MappingProfile', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    customers = db.relationship('CustomerDb', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    suppliers = db.relationship('SupplierDb', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    products = db.relationship('ProductDb', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    gl_accounts = db.relationship('GeneralLedgerAccountDb', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    tax_table_entries = db.relationship('TaxTableEntryDb', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
