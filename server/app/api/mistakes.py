"""错题本。"""

from flask import Blueprint, request
from sqlalchemy import or_

from ..extensions import db
from ..models import Mistake
from ..utils import ApiError, as_int, login_required_user, ok, paginate, pagination, payload, require

bp = Blueprint("mistakes", __name__, url_prefix="/api/mistakes")

# prompt/reason/answer 是 Text 不限长；knowledge_point / image 与列宽对齐，避免 1406 → 500
COLUMN_MAX_LENGTHS = {"knowledge_point": 64, "image": 255}


@bp.get("")
def list_mistakes():
    user = login_required_user()
    page, size = pagination()
    query = Mistake.query.filter_by(user_id=user.id)
    if request.args.get("mastery") not in (None, "", "all"):
        query = query.filter(Mistake.mastery == as_int(request.args.get("mastery"), 0))
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Mistake.prompt.like(like), Mistake.knowledge_point.like(like), Mistake.reason.like(like))
        )
    result = paginate(query.order_by(Mistake.created_at.desc()), page, size)
    result["list"] = [m.to_dict() for m in result["list"]]
    return ok(result)


@bp.post("")
def create_mistake():
    user = login_required_user()
    data = payload()
    require(data, "prompt")
    mistake = Mistake(
        user_id=user.id,
        prompt=str(data["prompt"]).strip(),
        reason=str(data.get("reason") or "").strip(),
        answer=str(data.get("answer") or "").strip(),
        knowledge_point=str(data.get("knowledgePoint") or "").strip()[:64],
        image=str(data.get("image") or "")[:255],
        mastery=as_int(data.get("mastery"), 0, minimum=0),
        source_post_id=as_int(data.get("sourcePostId"), None),
    )
    db.session.add(mistake)
    db.session.commit()
    return ok(mistake.to_dict(), 201)


@bp.patch("/<int:mistake_id>")
def update_mistake(mistake_id: int):
    user = login_required_user()
    mistake = db.session.get(Mistake, mistake_id)
    if mistake is None or mistake.user_id != user.id:
        raise ApiError("错题不存在", 404)
    data = payload()
    for field, column in (
        ("prompt", "prompt"),
        ("reason", "reason"),
        ("answer", "answer"),
        ("knowledgePoint", "knowledge_point"),
        ("image", "image"),
    ):
        if field in data:
            value = str(data.get(field) or "").strip()
            max_len = COLUMN_MAX_LENGTHS.get(column)
            setattr(mistake, column, value[:max_len] if max_len else value)
    if data.get("mastery") is not None:
        mistake.mastery = min(2, as_int(data["mastery"], mistake.mastery, minimum=0))
    db.session.commit()
    return ok(mistake.to_dict())


@bp.delete("/<int:mistake_id>")
def delete_mistake(mistake_id: int):
    user = login_required_user()
    mistake = db.session.get(Mistake, mistake_id)
    if mistake is None or mistake.user_id != user.id:
        raise ApiError("错题不存在", 404)
    db.session.delete(mistake)
    db.session.commit()
    return ok({"id": mistake_id})
