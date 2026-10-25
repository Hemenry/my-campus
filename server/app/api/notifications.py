"""消息中心。"""

from flask import Blueprint, request

from ..extensions import db
from ..models import Notification
from ..utils import ApiError, as_int, login_required_user, ok, payload

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
def list_notifications():
    user = login_required_user()
    query = Notification.query.filter_by(recipient_id=user.id)
    notice_type = (request.args.get("type") or "all").strip()
    if notice_type != "all":
        query = query.filter(Notification.type == notice_type)
    if request.args.get("unread") in ("1", "true"):
        query = query.filter(Notification.is_read.is_(False))

    rows = query.order_by(Notification.created_at.desc()).limit(100).all()
    unread = Notification.query.filter_by(recipient_id=user.id, is_read=False).count()
    return ok({"list": [n.to_dict() for n in rows], "unreadCount": unread})


@bp.post("/read")
def mark_read():
    user = login_required_user()
    data = payload()
    query = Notification.query.filter_by(recipient_id=user.id, is_read=False)
    ids = data.get("ids")
    if isinstance(ids, list) and ids:
        # 只取合法正整数，["abc"] 之类的脏数据不再把 int() 撑成 500
        valid_ids = [num for i in ids if (num := as_int(i, None)) is not None and num > 0]
        if not valid_ids:
            raise ApiError("ids 不合法", 422)
        query = query.filter(Notification.id.in_(valid_ids))
    updated = query.update({Notification.is_read: True}, synchronize_session=False)
    db.session.commit()
    return ok({"updated": updated})
