"""广场：帖子列表、详情、发布、点赞、收藏、回答、采纳。"""

from flask import Blueprint, request, session
from sqlalchemy import case, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..extensions import db
from ..models import Answer, AnswerLike, Collection, Comment, Notification, Post, PostLike, Tag, User, TYPE_LABELS
from ..utils import ApiError, current_user, login_required_user, ok, paginate, pagination, payload, require

bp = Blueprint("posts", __name__, url_prefix="/api")

LABEL_TO_TYPE = {label: key for key, label in TYPE_LABELS.items()}
SORT_CHOICES = {"latest", "hot", "unanswered"}


def get_post(post_id: int, viewer: User | None = None, options=None) -> Post:
    """取帖并做可见性校验：非 public 的帖子只有作者本人能看（school/private 同规则）。"""
    post = db.session.get(Post, post_id, options=options)
    if post is None or post.status == "offline":
        raise ApiError("内容不存在或已被下架", 404)
    if post.visibility != "public" and (viewer is None or viewer.id != post.user_id):
        raise ApiError("内容不存在或已被下架", 404)
    return post


def resolve_post_ids(user_id: int, ids: list[int], table, column_name: str) -> set[int]:
    """批量查询「我是否点赞 / 收藏过」，避免 N+1。"""
    if not user_id or not ids:
        return set()
    column = getattr(table, column_name)
    rows = table.query.filter(table.user_id == user_id, column.in_(ids)).all()
    return {getattr(row, column_name) for row in rows}


@bp.get("/posts")
def list_posts():
    page, size = pagination()
    category = (request.args.get("category") or "推荐").strip()
    keyword = (request.args.get("keyword") or "").strip()
    sort = (request.args.get("sort") or "latest").strip()
    subject = (request.args.get("subject") or "").strip()

    query = Post.query.options(joinedload(Post.author)).filter(
        Post.visibility == "public", Post.status != "offline"
    )

    post_type = LABEL_TO_TYPE.get(category, category if category in TYPE_LABELS else None)
    if post_type:
        query = query.filter(Post.type == post_type)
    if subject:
        query = query.filter(Post.subject == subject)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Post.title.like(like), Post.content.like(like)))

    if sort == "hot":
        query = query.order_by((Post.like_count * 2 + Post.answer_count * 3 + Post.collect_count).desc(), Post.id.desc())
    elif sort == "unanswered":
        query = query.filter(Post.answer_count == 0).order_by(Post.created_at.desc())
    else:
        query = query.order_by(Post.created_at.desc(), Post.id.desc())

    result = paginate(query, page, size)
    user = current_user()
    ids = [p.id for p in result["list"]]
    liked = resolve_post_ids(user.id if user else None, ids, PostLike, "post_id")
    collected = set()
    if user and ids:
        rows = Collection.query.filter(
            Collection.user_id == user.id, Collection.target_type == "post", Collection.target_id.in_(ids)
        ).all()
        collected = {row.target_id for row in rows}

    result["list"] = [
        {**p.to_dict(), "isLiked": p.id in liked, "isCollected": p.id in collected} for p in result["list"]
    ]
    return ok(result)


@bp.get("/posts/<int:post_id>")
def post_detail(post_id: int):
    user = current_user()
    post = get_post(
        post_id,
        user,
        options=(
            joinedload(Post.author),
            selectinload(Post.answers).joinedload(Answer.author),
            selectinload(Post.tags),
        ),
    )

    data = post.to_dict(detail=True)
    comments = (
        Comment.query.options(joinedload(Comment.author))
        .filter_by(target_type="post", target_id=post.id)
        .order_by(Comment.id.asc())
        .all()
    )
    data["comments"] = [c.to_dict() for c in comments]
    data["isLiked"] = bool(
        user and PostLike.query.filter_by(user_id=user.id, post_id=post.id).first()
    )
    data["isCollected"] = bool(
        user
        and Collection.query.filter_by(user_id=user.id, target_type="post", target_id=post.id).first()
    )
    data["isOwner"] = bool(user and user.id == post.user_id)

    # 浏览数去重：同一会话只计一次，刷新页面不会反复 +1。
    # 放在序列化之后再提交，避免事务提交把预加载的关联全部过期（否则详情页又变回 N+1）。
    viewed = session.get("viewed_posts") or []
    if post.id not in viewed:
        db.session.execute(
            update(Post)
            .where(Post.id == post.id)
            .values(view_count=Post.view_count + 1)
            .execution_options(synchronize_session=False)
        )
        db.session.commit()
        viewed = (viewed + [post.id])[-100:]
        session["viewed_posts"] = viewed
        data["viewCount"] = (data.get("viewCount") or 0) + 1
    return ok(data)


@bp.post("/posts")
def create_post():
    user = login_required_user()
    data = payload()
    require(data, "title", "type")

    post_type = LABEL_TO_TYPE.get(str(data["type"]), str(data["type"]))
    if post_type not in TYPE_LABELS:
        raise ApiError("内容类型不合法", 422)

    post = Post(
        type=post_type,
        title=str(data["title"]).strip()[:120],
        content=str(data.get("content") or "").strip(),
        images=[str(i) for i in (data.get("images") or [])][:9],
        subject=str(data.get("subject") or "").strip()[:32],
        topics=[str(t)[:32] for t in (data.get("topics") or [])][:5],
        visibility=str(data.get("visibility") or "public")[:16],
        user_id=user.id,
    )
    db.session.add(post)
    db.session.flush()

    for name in post.topics:
        tag = Tag.query.filter_by(name=name).first()
        if tag is None:
            tag = Tag(name=name, type="topic")
            db.session.add(tag)
            db.session.flush()
        post.tags.append(tag)

    db.session.commit()
    return ok(post.to_dict(detail=True), 201)


@bp.delete("/posts/<int:post_id>")
def delete_post(post_id: int):
    user = login_required_user()
    post = get_post(post_id, user)
    if post.user_id != user.id:
        raise ApiError("只能删除自己发布的内容", 403)
    post.status = "offline"
    # 下架后清掉收藏关系，避免「收藏夹里有条目、点进去 404」
    Collection.query.filter_by(target_type="post", target_id=post.id).delete(synchronize_session=False)
    db.session.commit()
    return ok({"id": post_id, "status": "offline"})


@bp.post("/posts/<int:post_id>/like")
def toggle_like(post_id: int):
    user = login_required_user()
    post = get_post(post_id, user)
    existing = PostLike.query.filter_by(user_id=user.id, post_id=post.id).first()
    if existing:
        db.session.delete(existing)
        # 计数器用 SQL 原子增减，避免读改写丢失更新；下限钳到 0
        db.session.execute(
            update(Post)
            .where(Post.id == post.id)
            .values(like_count=case((Post.like_count > 1, Post.like_count - 1), else_=0))
        )
        liked = False
    else:
        try:
            with db.session.begin_nested():
                db.session.add(PostLike(user_id=user.id, post_id=post.id))
                db.session.flush()
        except IntegrityError:
            # 并发重复点赞被唯一约束拦下：幂等返回已点赞，不再重复 +1
            liked = True
        else:
            db.session.execute(
                update(Post).where(Post.id == post.id).values(like_count=Post.like_count + 1)
            )
            liked = True
    db.session.commit()
    return ok({"liked": liked, "likeCount": post.like_count})


@bp.post("/posts/<int:post_id>/collect")
def toggle_collect(post_id: int):
    user = login_required_user()
    post = get_post(post_id, user)
    existing = Collection.query.filter_by(
        user_id=user.id, target_type="post", target_id=post.id
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.execute(
            update(Post)
            .where(Post.id == post.id)
            .values(collect_count=case((Post.collect_count > 1, Post.collect_count - 1), else_=0))
        )
        collected = False
    else:
        try:
            with db.session.begin_nested():
                db.session.add(Collection(user_id=user.id, target_type="post", target_id=post.id))
                db.session.flush()
        except IntegrityError:
            collected = True
        else:
            db.session.execute(
                update(Post).where(Post.id == post.id).values(collect_count=Post.collect_count + 1)
            )
            collected = True
    db.session.commit()
    return ok({"collected": collected, "collectCount": post.collect_count})


@bp.post("/posts/<int:post_id>/answers")
def create_answer(post_id: int):
    user = login_required_user()
    post = get_post(post_id, user)
    data = payload()
    require(data, "content")
    if post.user_id == user.id:
        raise ApiError("不能回答自己的帖子", 422)

    answer = Answer(
        post_id=post.id,
        user_id=user.id,
        content=str(data["content"]).strip(),
        images=[str(i) for i in (data.get("images") or [])][:9],
    )
    db.session.add(answer)
    db.session.execute(update(Post).where(Post.id == post.id).values(answer_count=Post.answer_count + 1))
    db.session.add(
        Notification(
            recipient_id=post.user_id,
            type="answer",
            actor_id=user.id,
            target_type="post",
            target_id=post.id,
            summary=f"{user.nickname} 回答了你的《{post.title}》",
        )
    )
    db.session.commit()
    return ok(answer.to_dict(), 201)


@bp.post("/answers/<int:answer_id>/like")
def toggle_answer_like(answer_id: int):
    user = login_required_user()
    answer = db.session.get(Answer, answer_id)
    if answer is None:
        raise ApiError("回答不存在", 404)
    existing = AnswerLike.query.filter_by(user_id=user.id, answer_id=answer.id).first()
    if existing:
        db.session.delete(existing)
        db.session.execute(
            update(Answer)
            .where(Answer.id == answer.id)
            .values(like_count=case((Answer.like_count > 1, Answer.like_count - 1), else_=0))
        )
        liked = False
    else:
        try:
            with db.session.begin_nested():
                db.session.add(AnswerLike(user_id=user.id, answer_id=answer.id))
                db.session.flush()
        except IntegrityError:
            liked = True
        else:
            db.session.execute(
                update(Answer).where(Answer.id == answer.id).values(like_count=Answer.like_count + 1)
            )
            liked = True
    db.session.commit()
    return ok({"liked": liked, "likeCount": answer.like_count})


@bp.post("/answers/<int:answer_id>/adopt")
def adopt_answer(answer_id: int):
    user = login_required_user()
    answer = db.session.get(Answer, answer_id)
    if answer is None:
        raise ApiError("回答不存在", 404)
    post = answer.post
    if post.user_id != user.id:
        raise ApiError("只有提问者可以采纳答案", 403)
    if post.status == "adopted":
        raise ApiError("这条内容已经采纳过答案了", 409)

    for item in post.answers:
        item.is_adopted = item.id == answer.id
    post.status = "adopted"

    author = answer.author
    if author:
        db.session.execute(
            update(User).where(User.id == author.id).values(adopted_count=User.adopted_count + 1)
        )
        db.session.add(
            Notification(
                recipient_id=author.id,
                type="adopt",
                actor_id=user.id,
                target_type="post",
                target_id=post.id,
                summary=f"{user.nickname} 采纳了你在《{post.title}》下的回答",
            )
        )
    db.session.commit()
    return ok(answer.to_dict())
