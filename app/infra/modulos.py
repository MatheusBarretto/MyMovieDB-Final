from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.services.secret_service import SecretsManager

bootstrap = Bootstrap5()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
secrets_manager = SecretsManager(verify_salt_integrity=True)
