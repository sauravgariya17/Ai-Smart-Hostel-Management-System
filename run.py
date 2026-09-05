#===============================================================================
#       python run.py
#===============================================================================


import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = app.config.get("DEBUG", True)

    print("=" * 60)
    print(" AI-Powered Smart Hostel Management System")
    print(f" Running on http://{host}:{port}  (debug={debug})")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)
