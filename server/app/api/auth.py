"""认证：注册、登录、当前用户。"""

import re

from flask import Blueprint, request
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models import Notification, User
from ..rate_limit import SlidingWindowLimiter
from ..utils import ApiError, login_required_user, ok, payload, require

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EDITABLE_FIELDS = ("nickname", "avatar", "school", "dept", "grade", "bio")
# 与 models/user.py 的列宽一一对应，超长直接截断，避免 MySQL 1406 → 500
FIELD_MAX_LENGTHS = {"nickname": 32, "avatar": 255, "school": 64, "dept": 64, "grade": 16, "bio": 255}

# 5 分钟内同一 IP+用户名失败 5 次即拒绝，防撞库
login_limiter = SlidingWindowLimiter(limit=5, window_seconds=5 * 60)


def client_ip() -> str:
    return (request.headers.get("X-Real-IP") or request.remote_addr or "unknown").strip()


def issue_token(user: User) -> str:
    return create_access_token(identity=str(user.id))


@bp.post("/register")
def register():
    data = payload()
    require(data, "username", "password")
    username = str(data["username"]).strip()
    password = str(data["password"])
    nickname = str(data.get("nickname") or username).strip()[:32]

    if not USERNAME_RE.match(username):
        raise ApiError("用户名只能是 3~32 位字母、数字或下划线", 422)
    if len(password) < 6:
        raise ApiError("密码至少 6 位", 422)
    if User.query.filter_by(username=username).first():
        raise ApiError("这个用户名已经被占用了", 409)

    user = User(username=username, nickname=nickname)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    db.session.add(
        Notification(
            recipient_id=user.id,
            type="system",
            target_type="system",
            summary="欢迎来到 GeekCampus：先发一条求助，或者导入一本词书试试。",
        )
    )
    db.session.commit()
    return ok({"token": issue_token(user), "user": user.to_dict()}, 201)


@bp.post("/login")
def login():
    data = payload()
    require(data, "username", "password")
    username = str(data["username"]).strip()

    # 先查限流再校验密码：只累计失败次数，登录成功即清零
    key = f"{client_ip()}|{username.lower()}"
    if login_limiter.exceeded(key):
        raise ApiError("登录尝试过于频繁，请 5 分钟后再试", 429)

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(str(data["password"])):
        login_limiter.hit(key)
        raise ApiError("用户名或密码不正确", 401)
    login_limiter.reset(key)
    return ok({"token": issue_token(user), "user": user.to_dict()})


@bp.get("/me")
def me():
    user = login_required_user()
    return ok(user.to_dict(with_private=True))


@bp.patch("/me")
def update_me():
    user = login_required_user()
    data = payload()
    for field in EDITABLE_FIELDS:
        if field in data:
            value = data.get(field)
            max_len = FIELD_MAX_LENGTHS[field]
            setattr(user, field, str(value).strip()[:max_len] if value is not None else "")
    if not user.nickname:
        raise ApiError("昵称不能为空", 422)
    db.session.commit()
    return ok(user.to_dict(with_private=True))
