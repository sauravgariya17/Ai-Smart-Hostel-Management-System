"""
app/main/routes.py
---------------------
Server-rendered page routes. These views only render templates/shells;
authentication state and role-based UI switching happen client-side in
static/js/main.js, auth.js, and each module's own JS file by reading the
JWT stored after a successful login API call.
"""

from flask import render_template, redirect, url_for

from app.main import main_bp


# ======================================================================
# Public / Auth pages
# ======================================================================

@main_bp.route("/")
def index():
    return redirect(url_for("main.login_page"))


@main_bp.route("/login")
def login_page():
    return render_template("auth/login.html")


@main_bp.route("/student/register")
def student_register_page():
    """Public student self-registration page."""
    return render_template("auth/student_register.html")


@main_bp.route("/forgot-password")
def forgot_password_page():
    return render_template("auth/forgot_password.html")


@main_bp.route("/reset-password")
def reset_password_page():
    return render_template("auth/reset_password.html")


# ======================================================================
# Dashboards
# ======================================================================

@main_bp.route("/dashboard")
def dashboard_page():
    """
    Generic dashboard entry point. Role is only known client-side (JWT in
    localStorage), so this shell immediately redirects to the correct
    role-specific dashboard page once main.js/TokenStore has run.
    """
    return render_template("dashboard/dashboard_redirect.html")


@main_bp.route("/admin/dashboard")
def admin_dashboard_page():
    return render_template("dashboard/admin_dashboard.html")


@main_bp.route("/warden/dashboard")
def warden_dashboard_page():
    return render_template("dashboard/warden_dashboard.html")


@main_bp.route("/student/dashboard")
def student_dashboard_page():
    return render_template("dashboard/student_dashboard.html")


# ======================================================================
# Hostel Management Modules
# ======================================================================

@main_bp.route("/students")
def students_page():
    return render_template("students/manage.html")


@main_bp.route("/wardens")
def wardens_page():
    return render_template("wardens/manage.html")


@main_bp.route("/hostels")
def hostels_page():
    return render_template("hostels/manage.html")


@main_bp.route("/rooms")
def rooms_page():
    return render_template("rooms/manage.html")


@main_bp.route("/fees")
def fees_page():
    return render_template("fees/manage.html")


@main_bp.route("/visitors")
def visitors_page():
    return render_template("visitors/manage.html")


@main_bp.route("/attendance")
def attendance_page():
    return render_template("attendance/manage.html")


@main_bp.route("/complaints")
def complaints_page():
    return render_template("complaints/manage.html")


@main_bp.route("/maintenance")
def maintenance_page():
    return render_template("maintenance/manage.html")


@main_bp.route("/notifications")
def notifications_page():
    return render_template("notifications/list.html")


@main_bp.route("/reports")
def reports_page():
    return render_template("reports/reports.html")
