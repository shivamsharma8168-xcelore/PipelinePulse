import time

from flask import Flask
from flask_cors import CORS
from sqlalchemy.exc import OperationalError

from .config import Config
from .extensions import db
from .routes import api


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["FRONTEND_ORIGINS"]:
        CORS(
            app,
            resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
            supports_credentials=True,
        )
    db.init_app(app)
    app.register_blueprint(api)

    if app.config["AUTO_CREATE_TABLES"]:
        with app.app_context():
            _create_tables_with_retry()

    return app


def _create_tables_with_retry():
    for attempt in range(1, 8):
        try:
            db.create_all()
            return
        except OperationalError:
            if attempt == 7:
                raise
            time.sleep(2)
