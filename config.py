#============================================================================
#       config.py
#============================================================================
import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load variables from a .env file located at the project root
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get_bool(env_key: str, default: bool = False) -> bool:
    """Helper to safely parse boolean environment variables."""
    value = os.environ.get(env_key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _build_database_uri() -> str:
    """Build the SQLAlchemy database URI from discrete env vars,
    unless a full DATABASE_URL is explicitly provided."""
    explicit_url = os.environ.get("DATABASE_URL")
    if explicit_url:
        return explicit_url

    engine = os.environ.get("DB_ENGINE", "mysql+pymysql")
    username = os.environ.get("DB_USERNAME", "root")
    password = quote_plus(os.environ.get("DB_PASSWORD", ""))
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "smart_hostel_db")

    return f"{engine}://{username}:{password}@{host}:{port}/{name}"


class BaseConfig:
    """Common configuration shared across all environments."""

    # ---- Core Flask ----
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = False
    TESTING = False

    # ---- SQLAlchemy / MySQL ----
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # Verify connections before using (avoids "MySQL server gone away")
        "pool_recycle": 280,     # Recycle connections before MySQL's wait_timeout kicks in
    }

    # ---- JWT ----
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ERROR_MESSAGE_KEY = "message"

    # ---- Password Reset ----
    PASSWORD_RESET_TOKEN_EXPIRES_MINUTES = int(
        os.environ.get("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", 60)
    )
    FRONTEND_RESET_PASSWORD_URL = os.environ.get(
        "FRONTEND_RESET_PASSWORD_URL", "http://localhost:5000/reset-password"
    )

    # ---- Mail ----
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _get_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _get_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # ---- CORS ----
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # ---- Default Admin (used by seed_admin.py) ----
    DEFAULT_ADMIN_NAME = os.environ.get("DEFAULT_ADMIN_NAME", "Super Admin")
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@hostel.com")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@12345")

    # ----AI / ML model & dataset locations ----
    # Trained model artifacts (.joblib) produced by the scripts in ml/ and
    # loaded at runtime by app/ai/services/*. Kept outside the app package
    # since they are build artifacts, not application source code.
    ML_DIR = os.path.join(BASE_DIR, "ml")
    ML_MODELS_DIR = os.path.join(ML_DIR, "models")
    ML_DATASETS_DIR = os.path.join(ML_DIR, "datasets")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        **BaseConfig.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 10,
        "max_overflow": 20,
    }


# Mapping used by the application factory to select configuration by name.
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Return the configuration class based on the FLASK_ENV env variable."""
    env_name = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env_name, DevelopmentConfig)
