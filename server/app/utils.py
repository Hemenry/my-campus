"""统一响应、参数校验、分页与当前用户工具。"""

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from .extensions import db
from .models import User


class ApiError(Exception):
    """业务异常：由全局错误处理器转成统一 JSON。"""

    def __init__(self, message: str, status: int = 400, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code if code is not None else status


def ok(data=None, status: int = 200, **extra):
    payload = {"code": 0, "message": "ok", "data": data}
    payload.update(extra)
    return jsonify(payload), status


def payload() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    return data


def require(data: dict, *names: str) -> None:
    missing = [n for n in names if not str(data.get(n) or "").strip()]
    if missing:
        raise ApiError(f"缺少必填字段：{'、'.join(missing)}", 422)


def as_int(value, default=None, minimum=None, maximum=None):
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and num < minimum:
        return minimum
    if maximum is not None and num > maximum:
        return maximum
    return num


def pagination():
    page = as_int(request.args.get("page"), 1, minimum=1)
    size = as_int(request.args.get("pageSize"), 10, minimum=1)
    return page, min(size, 50)


def paginate(query, page: int, size: int) -> dict:
    total = query.order_by(None).count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "list": items,
        "total": total,
        "page": page,
        "pageSize": size,
        "hasMore": page * size < total,
    }


def current_user() -> User | None:
    """可选登录：带了有效 token 就返回用户，否则 None。"""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        return None
    if identity is None:
        return None
    return db.session.get(User, int(identity))


def login_required_user() -> User:
    user = current_user()
    if user is None:
        raise ApiError("登录状态已失效，请重新登录", 401, code=401)
    return user


def iso(value) -> str | None:
    return value.isoformat() if value else None
