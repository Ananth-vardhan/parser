"""Application bootstrap and factory helpers for the parser service."""
from __future__ import annotations

from dotenv import load_dotenv
from flask import Flask

from .config import get_config

load_dotenv()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application.

    The factory reads configuration from :mod:`app.config`, applies it to the
    Flask instance, and registers the project's blueprints.
    """

    app = Flask(__name__)

    resolved_config = get_config(config_name)
    app.config.from_object(resolved_config)
    # Store the dataclass settings so downstream code can access structured data.
    app.config["SETTINGS"] = resolved_config.SETTINGS

    _configure_logging(app)
    _register_blueprints(app)

    return app


def _configure_logging(app: Flask) -> None:
    log_level = app.config.get("LOG_LEVEL", "INFO")
    app.logger.setLevel(log_level)


def _register_blueprints(app: Flask) -> None:
    from .api import api_bp

    app.register_blueprint(api_bp)


__all__: list[str] = ["create_app"]
