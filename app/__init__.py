"""Flask application factory for the local Japanese practice chatbot."""

import logging
import time
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask import g, request

from app.config import Config
from app.db import init_db
from app.cli import register_cli


def _silence_noisy_http_loggers() -> None:
    """Keep httpcore/httpx from emitting DEBUG through the root logger.

    With APP_LOG_LEVEL=DEBUG, those libraries log during OpenAI/httpx calls. On
    Windows, RotatingFileHandler then hits ``RuntimeError: reentrant call``
    if a nested log runs while the same file is being written (common in
    background threads during cache refill).
    """
    for name in ("httpcore", "httpcore.http11", "httpx", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _configure_app_logging(app: Flask) -> None:
    log_path = app.config["LOG_PATH"]
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_level = getattr(logging, str(app.config["LOG_LEVEL"]).upper(), logging.INFO)
    root_logger.setLevel(root_level)
    _silence_noisy_http_loggers()

    existing_paths = {
        getattr(h, "baseFilename", None)
        for h in root_logger.handlers
        if isinstance(h, RotatingFileHandler)
    }
    if str(log_path) not in existing_paths:
        root_logger.addHandler(file_handler)

    app.logger.setLevel(root_level)
    app.logger.info("app logging initialized at %s", log_path)


def _configure_cost_logging(app: Flask) -> None:
    """One TSV row per successful LLM completion (token usage) in cost.log."""
    cost_path = app.config["COST_LOG_PATH"]
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_logger = logging.getLogger("app.cost")
    cost_logger.setLevel(logging.INFO)
    cost_logger.propagate = False
    resolved = str(cost_path.resolve())
    for h in cost_logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == resolved:
            return
    fh = RotatingFileHandler(
        cost_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(
        logging.Formatter("%(asctime)s\t%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    cost_logger.addHandler(fh)
    cost_logger.info(
        "kind\tmodel\tprompt_tokens\tcompletion_tokens\ttotal_tokens\tresult"
    )


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)
    _configure_app_logging(app)
    _configure_cost_logging(app)

    init_db(app)
    register_cli(app)

    from app.routes import bp as main_bp

    app.register_blueprint(main_bp)

    @app.before_request
    def _track_request_start() -> None:
        g._request_started_at = time.time()
        app.logger.info("request start %s %s", request.method, request.path)

    @app.after_request
    def _track_request_end(response):  # type: ignore[no-untyped-def]
        started = getattr(g, "_request_started_at", None)
        ms = -1
        if isinstance(started, (int, float)):
            ms = int((time.time() - started) * 1000)
        app.logger.info(
            "request end %s %s status=%s duration_ms=%s",
            request.method,
            request.path,
            response.status_code,
            ms,
        )
        return response

    @app.teardown_request
    def _track_request_exception(err):  # type: ignore[no-untyped-def]
        if err is not None:
            app.logger.exception("request failed %s %s error=%s", request.method, request.path, err)

    return app
