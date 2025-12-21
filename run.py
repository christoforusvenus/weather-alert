import os
from App import db, create_app

app = create_app()

if __name__ == "__main__":
    if os.getenv("FLASK_ENV", "development") != "production":
        with app.app_context():
            db.create_all()

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"

    app.run(host=host, port=port, debug=debug)
