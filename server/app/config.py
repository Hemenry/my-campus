"""应用配置。所有可变项走环境变量，便于本地 / 测试 / 生产切换。"""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# 生产（gunicorn / wsgi 默认）不认 FLASK_DEBUG；本地开发在 .env 里设 FLASK_DEBUG=1
DEBUG = _env_flag("FLASK_DEBUG")


def _require_secret(name: str, dev_fallback: str) -> str:
    """密钥缺失时：debug 允许用开发兜底值，生产直接启动失败，杜绝默认密钥被伪造 JWT。"""
    value = os.getenv(name)
    if value:
        return value
    if DEBUG:
        return dev_fallback
    raise RuntimeError(
        f"环境变量 {name} 未配置：生产环境禁止使用默认密钥（本地开发请设置 FLASK_DEBUG=1）"
    )


def _parse_cors_origins() -> list[str]:
    """跨域白名单，默认只放本地 Vite 开发服务器；生产同源部署不需要 CORS。

    - 未配置：http://localhost:5173 与 127.0.0.1:5173
    - 配成 *：允许任意来源（仅限开发）
    - 配成空串：禁止所有跨域（同源部署的最严形态）
    """
    raw = os.getenv("CORS_ORIGINS")
    if raw is None:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    raw = raw.strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def build_database_uri() -> str:
    """优先使用完整 DATABASE_URL，否则由分项配置拼装 MySQL 连接串。"""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "geekcampus")
    return (
        f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        "?charset=utf8mb4"
    )


class Config:
    DEBUG = DEBUG
    SECRET_KEY = _require_secret("SECRET_KEY", "geekcampus-dev-secret")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    JWT_SECRET_KEY = _require_secret("JWT_SECRET_KEY", "geekcampus-jwt-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_EXPIRES_DAYS", "7")))

    CORS_ORIGINS = _parse_cors_origins()

    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 单文件 8MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}

    API_PREFIX = "/api"
