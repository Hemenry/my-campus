"""模型公共基类与工具。"""

from datetime import datetime, timezone

from ..extensions import db


def utcnow() -> datetime:
    """MySQL DATETIME 不存时区，统一按 UTC 的 naive 时间落库。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
