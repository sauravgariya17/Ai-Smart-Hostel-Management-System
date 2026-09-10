"""
app/__init__.py
------------------
Flask application factory for the AI-Powered Smart Hostel Management
System. Centralizes:
  - Extension initialization (SQLAlchemy, Migrate, JWT, Bcrypt, CORS, Mail)
  - Blueprint registration
  - JWT callbacks (blacklist checking, custom error responses)
  - Global error handlers
"""

import logging

from flask import Flask, jsonify

from config import get_config
from app.extensions import db, migrate, jwt, bcrypt, cors, mail


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    _configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_jwt_callbacks(app)
    _register_error_handlers(app)

    return app


def _configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Ensure every model is imported so Flask-Migrate/Alembic can see all tables.
    with app.app_context():
        from app import models  # noqa: F401


def _register_blueprints(app: Flask) -> None:
    from app.auth import auth_bp
    from app.main import main_bp
    from app.students import students_bp
    from app.wardens import wardens_bp
    from app.hostels import hostels_bp
    from app.rooms import rooms_bp
    from app.fees import fees_bp
    from app.visitors import visitors_bp
    from app.attendance import attendance_bp
    from app.complaints import complaints_bp
    from app.maintenance import maintenance_bp
    from app.notifications import notifications_bp
    from app.reports import reports_bp
    from app.dashboard import dashboard_bp
    from app.ai import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(wardens_bp)
    app.register_blueprint(hostels_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(fees_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_bp)


def _register_jwt_callbacks(app: Flask) -> None:
    """Wire Flask-JWT-Extended into the TokenBlacklist table so that
    logged-out / revoked tokens are rejected on every subsequent request."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.models import TokenBlacklist
        jti = jwt_payload["jti"]
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has expired. Please log in again."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"success": False, "message": f"Invalid token: {reason}"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({"success": False, "message": "Authorization token is missing."}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has been revoked. Please log in again."}), 401


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return jsonify({"success": False, "message": "An internal server error occurred."}), 500
