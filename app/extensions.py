"""
app/extensions.py
------------------
Instantiates Flask extensions without binding them to an application.

Extensions are initialized here and later bound to the Flask app instance
inside the application factory (app/__init__.py) via `extension.init_app(app)`.
This pattern avoids circular imports across the models/blueprints.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
mail = Mail()
