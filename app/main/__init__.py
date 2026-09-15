"""
app/main/__init__.py
-----------------------
Defines the "main" blueprint responsible for rendering server-side HTML
pages (login, dashboard shell, forgot/reset password). All data-fetching
on these pages happens client-side via JavaScript calling the JSON API
exposed by the "auth" blueprint (and future feature blueprints).
"""

from flask import Blueprint

main_bp = Blueprint("main", __name__, template_folder="../templates")

from app.main import routes  # noqa: E402,F401
