from flask import Blueprint

wardens_bp = Blueprint("wardens_api", __name__, url_prefix="/api/wardens")

from app.wardens import routes  # noqa: E402,F401
