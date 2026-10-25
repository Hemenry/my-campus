"""评论：帖子与回答通用。"""

from flask import Blueprint, request
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Answer, Comment, Notification
from ..utils import ApiError, as_int, current_user, login_required_user, ok, payload, require
from .posts import get_post

bp = Blueprint("comments", __name__, url_prefix="/api/comments")


def resolve_target(target_type: str, target_id: int, viewer=None) -> int | None:
    """校验评论目标存在且对当前访问者可见，返回目标作者 id（找不到/不可见一律 404）。"""
    if target_type == "post":
        post = get_post(target_id, viewer)
        return post.user_id
    if target_type == "answer":
        answer = db.session.get(Answer, target_id)
        if answer is None:
            raise ApiError("评论目标不存在", 404)
        get_post(answer.post_id, viewer)  # 回答随帖子一起做可见性校验
        return answer.user_id
    raise ApiError("评论目标不合法", 422)


@bp.get("")
def list_comments():
    target_type = request.args.get("targetType", "post")
    target_id = as_int(request.args.get("targetId"), 0)
    if not target_id:
        raise ApiError("缺少 targetId", 422)
    resolve_target(target_type, target_id, current_user())
    rows = (
        Comment.query.options(joinedload(Comment.author))
        .filter_by(target_type=target_type, target_id=target_id)
        .order_by(Comment.id.asc())
        .all()
    )
    return ok([c.to_dict() for c in rows])


@bp.post("")
def create_comment():
    user = login_required_user()
    data = payload()
    require(data, "targetType", "targetId", "content")
    target_type = str(data["targetType"])
    target_id = as_int(data["targetId"], 0)
    if target_type not in ("post", "answer") or not target_id:
        raise ApiError("评论目标不合法", 422)
    owner_id = resolve_target(target_type, target_id, user)

    parent_id = as_int(data.get("parentId"), None)
    if parent_id:
        parent = db.session.get(Comment, parent_id)
        if parent is None:
            raise ApiError("父评论不存在", 404)
        if parent.target_type != target_type or parent.target_id != target_id:
            raise ApiError("父评论不属于当前评论目标", 422)

    comment = Comment(
        target_type=target_type,
        target_id=target_id,
        user_id=user.id,
        parent_id=parent_id,
        content=str(data["content"]).strip()[:1000],
    )
    db.session.add(comment)
    db.session.flush()

    if owner_id and owner_id != user.id:
        db.session.add(
            Notification(
                recipient_id=owner_id,
                type="comment",
                actor_id=user.id,
                target_type=target_type,
                target_id=target_id,
                summary=f"{user.nickname} 评论了你的内容：{comment.content[:24]}",
            )
        )
    db.session.commit()
    return ok(comment.to_dict(), 201)


@bp.delete("/<int:comment_id>")
def delete_comment(comment_id: int):
    user = login_required_user()
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        raise ApiError("评论不存在", 404)
    if comment.user_id != user.id:
        raise ApiError("只能删除自己的评论", 403)
    db.session.delete(comment)
    db.session.commit()
    return ok({"id": comment_id})
