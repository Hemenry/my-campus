"""Flask 应用工厂。"""

import logging
import os

from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import cors, db, jwt, migrate
from .utils import ApiError, ok

logger = logging.getLogger("geekcampus")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return {"code": err.code, "message": err.message, "data": None}, err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        return {"code": err.code, "message": err.description, "data": None}, err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        db.session.rollback()
        logger.exception("未捕获异常: %s", err)
        return {"code": 500, "message": "服务器开小差了，请稍后再试", "data": None}, 500


def register_jwt_callbacks() -> None:
    @jwt.unauthorized_loader
    def missing_token(reason: str):
        return {"code": 401, "message": "请先登录", "data": None}, 401

    @jwt.invalid_token_loader
    def invalid_token(reason: str):
        return {"code": 401, "message": "登录凭证无效", "data": None}, 401

    @jwt.expired_token_loader
    def expired_token(header, data):
        return {"code": 401, "message": "登录已过期，请重新登录", "data": None}, 401


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.json.ensure_ascii = False  # 让中文直接输出，不转 \uXXXX

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    register_jwt_callbacks()

    upload_dir = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    from . import models  # noqa: F401  注册全部元数据，Alembic 依赖此导入
    from .api import register_blueprints

    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(upload_dir, filename)

    @app.get("/api/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return ok({"status": "healthy", "database": db.engine.url.database})

    return app
