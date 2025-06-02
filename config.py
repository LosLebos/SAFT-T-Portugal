import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here_please_change'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'saft_app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
