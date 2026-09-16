from pathlib import Path

from flask import Flask, render_template

from app.config import Config
from app.database import init_db


BASE_DIR = Path(__file__).resolve().parent.parent


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        static_url_path="/static",
    )
    app.config.from_object(Config)

    init_db(app)

    with app.app_context():
        from app.services.seed_service import seed_demo_data

        seed_demo_data()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    from app.routes.auth import auth_bp
    from app.routes.lessons import lessons_bp
    from app.routes.reference import reference_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(reference_bp, url_prefix="/api")
    app.register_blueprint(lessons_bp, url_prefix="/api")

    return app
