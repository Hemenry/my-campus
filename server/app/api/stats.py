"""个人主页与数据概览。"""

from datetime import date, datetime, timedelta

from flask import Blueprint
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Answer,
    Checkin,
    Collection,
    Mistake,
    Notification,
    Post,
    ReviewRecord,
    User,
    WordEntry,
    Wordbook,
)
from ..utils import ApiError, login_required_user, ok

bp = Blueprint("stats", __name__, url_prefix="/api")


@bp.get("/users/<int:user_id>")
def user_profile(user_id: int):
    viewer = login_required_user()  # 免登录可遍历用户 ID，这里要求登录
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("用户不存在", 404)
    data = user.to_dict()
    if viewer.id != user.id:
        data.pop("username", None)  # username 只给本人看，防止撞库枚举
    post_count = Post.query.filter_by(user_id=user.id, status="offline").count()
    answer_count = Answer.query.filter_by(user_id=user.id).count()
    return ok(
        {
            **data,
            "postCount": Post.query.filter_by(user_id=user.id).filter(Post.status != "offline").count(),
            "answerCount": answer_count,
            "offlineCount": post_count,
            "wordbookCount": Wordbook.query.filter_by(user_id=user.id).count(),
        }
    )


@bp.get("/stats/summary")
def summary():
    user = login_required_user()
    today = date.today()
    week_start = today - timedelta(days=6)

    post_count = Post.query.filter(Post.user_id == user.id, Post.status != "offline").count()
    answer_count = Answer.query.filter_by(user_id=user.id).count()
    adopted_count = Answer.query.filter_by(user_id=user.id, is_adopted=True).count()
    mistake_count = Mistake.query.filter_by(user_id=user.id).count()
    mastered_mistake = Mistake.query.filter_by(user_id=user.id, mastery=2).count()
    collect_count = Collection.query.filter_by(user_id=user.id).count()
    wordbook_count = Wordbook.query.filter_by(user_id=user.id).count()

    # 与 english.list_wordbooks 的 dueCount 同口径：未掌握且（没排期 / 已到期）
    today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())
    due_words = (
        db.session.query(func.count(WordEntry.id))
        .join(Wordbook, Wordbook.id == WordEntry.wordbook_id)
        .filter(
            Wordbook.user_id == user.id,
            WordEntry.status != "mastered",
            (WordEntry.next_review_at.is_(None)) | (WordEntry.next_review_at < today_end),
        )
        .scalar()
        or 0
    )
    today_review = (
        db.session.query(func.coalesce(func.sum(ReviewRecord.word_count), 0))
        .filter(ReviewRecord.user_id == user.id, ReviewRecord.date == today)
        .scalar()
        or 0
    )
    week_review = (
        db.session.query(func.coalesce(func.sum(ReviewRecord.word_count), 0))
        .filter(ReviewRecord.user_id == user.id, ReviewRecord.date >= week_start)
        .scalar()
        or 0
    )
    week_checkin = Checkin.query.filter(Checkin.user_id == user.id, Checkin.date >= week_start).count()
    unread = Notification.query.filter_by(recipient_id=user.id, is_read=False).count()

    return ok(
        {
            "user": user.to_dict(),
            "postCount": post_count,
            "answerCount": answer_count,
            "adoptedCount": adopted_count,
            "mistakeCount": mistake_count,
            "masteredMistakeCount": mastered_mistake,
            "collectCount": collect_count,
            "wordbookCount": wordbook_count,
            "dueWords": due_words,
            "todayReview": int(today_review),
            "weekReview": int(week_review),
            "weekCheckin": week_checkin,
            "streakDays": user.streak_days,
            "totalCheckinDays": user.total_checkin_days,
            "unreadCount": unread,
            "checkedInToday": Checkin.query.filter_by(user_id=user.id, date=today).first() is not None,
        }
    )


@bp.get("/me/posts")
def my_posts():
    user = login_required_user()
    rows = (
        Post.query.filter(Post.user_id == user.id, Post.status != "offline")
        .order_by(Post.created_at.desc())
        .limit(50)
        .all()
    )
    return ok([p.to_dict() for p in rows])


@bp.get("/me/collections")
def my_collections():
    user = login_required_user()
    rows = (
        Collection.query.filter_by(user_id=user.id, target_type="post")
        .order_by(Collection.created_at.desc())
        .all()
    )
    ids = [r.target_id for r in rows]
    posts = (
        Post.query.filter(Post.id.in_(ids), Post.status != "offline").all() if ids else []
    )
    order = {pid: idx for idx, pid in enumerate(ids)}
    posts.sort(key=lambda p: order.get(p.id, 0))
    return ok([{**p.to_dict(), "isCollected": True} for p in posts])
