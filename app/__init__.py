from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

bootstrap = Bootstrap()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User # Import here to avoid circular dependency
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    login_manager.init_app(app)

    from app import models # Ensure this is after db init and before routes that might use models indirectly

    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .routes.data_input import data_input_bp
    app.register_blueprint(data_input_bp)

    from .routes.mapping import mapping_bp
    app.register_blueprint(mapping_bp)

    from .routes.masterfiles import masterfiles_bp # Import new blueprint
    app.register_blueprint(masterfiles_bp)    # Register new blueprint

    app.jinja_env.globals['APP_BRANDING'] = "SAF-T Generator PT"

    return app
