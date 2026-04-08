"""Flask application factory for the local Japanese practice chatbot."""

from flask import Flask

from app.config import Config
from app.db import init_db
from app.cli import register_cli


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    init_db(app)
    register_cli(app)

    from app.routes import bp as main_bp

    app.register_blueprint(main_bp)

    return app
