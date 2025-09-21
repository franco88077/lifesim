"""Application factory for Lifesim."""
from __future__ import annotations

from flask import Flask

from .config import Config
from .extensions import db
from .logging_service import log_manager


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    db.init_app(app)
    log_manager.init_app(app)

    with app.app_context():
        db.create_all()

    from .index import bp as index_bp
    from .banking import bp as banking_bp
    from .real_estate import bp as real_estate_bp
    from .shop import bp as shop_bp
    from .job import bp as job_bp
    from .logging import bp as logging_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(banking_bp, url_prefix="/banking")
    app.register_blueprint(real_estate_bp, url_prefix="/real-estate")
    app.register_blueprint(shop_bp, url_prefix="/shop")
    app.register_blueprint(job_bp, url_prefix="/job")
    app.register_blueprint(logging_bp, url_prefix="/logs")

    for component in ("Home", "Banking", "RealEstate", "Shop", "Job", "Logging"):
        log_manager.register_component(component)

    @app.context_processor
    def inject_globals() -> dict[str, object]:
        """Inject shared template variables."""
        return {
            "environment": app.config.get("ENVIRONMENT", "development"),
            "log_levels": log_manager.available_levels,
            "log_components": log_manager.available_components,
        }

    return app
