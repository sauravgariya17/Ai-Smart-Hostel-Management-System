#===============================================================================
# Admin
#===============================================================================

from app import create_app
from app.extensions import db
from app.models import User, RoleEnum


def seed_admin():
    app = create_app()

    with app.app_context():
        db.create_all()

        admin_email = app.config["DEFAULT_ADMIN_EMAIL"].lower().strip()
        existing = User.query.filter_by(email=admin_email).first()

        if existing:
            print(f"[skip] Admin with email '{admin_email}' already exists.")
            return

        admin = User(
            name=app.config["DEFAULT_ADMIN_NAME"],
            email=admin_email,
            role=RoleEnum.ADMIN,
            is_active=True,
            is_verified=True,
        )
        admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])

        db.session.add(admin)
        db.session.commit()

        print("[success] Default admin account created:")
        print(f"          email:    {admin_email}")
        print(f"          password: {app.config['DEFAULT_ADMIN_PASSWORD']}")
        print("          Please log in and change this password immediately.")


if __name__ == "__main__":
    seed_admin()
