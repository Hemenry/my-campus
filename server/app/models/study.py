"""学习域模型：错题、词书、词条、复习记录、打卡、学习计划。"""

from ..extensions import db
from .base import TimestampMixin

MASTERY_LABELS = {0: "未掌握", 1: "复习中", 2: "已掌握"}
ENTRY_STATUS_LABELS = {"new": "未学", "learning": "学习中", "mastered": "已掌握"}


class Mistake(TimestampMixin, db.Model):
    __tablename__ = "mistakes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image = db.Column(db.String(255), default="")
    prompt = db.Column(db.Text, default="")          # 题干
    reason = db.Column(db.Text, default="")          # 我的错因
    answer = db.Column(db.Text, default="")          # 正确答案
    knowledge_point = db.Column(db.String(64), default="")
    mastery = db.Column(db.SmallInteger, default=0, nullable=False, index=True)
    source_post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image": self.image,
            "prompt": self.prompt,
            "reason": self.reason,
            "answer": self.answer,
            "knowledgePoint": self.knowledge_point,
            "mastery": self.mastery,
            "masteryLabel": MASTERY_LABELS.get(self.mastery, "未掌握"),
            "sourcePostId": self.source_post_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Wordbook(TimestampMixin, db.Model):
    __tablename__ = "wordbooks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255), default="")
    source = db.Column(db.String(16), default="manual", nullable=False)  # recommend / pdf / manual
    color = db.Column(db.String(16), default="#1F8A6B")
    total_count = db.Column(db.Integer, default=0, nullable=False)
    mastered_count = db.Column(db.Integer, default=0, nullable=False)

    owner = db.relationship("User", back_populates="wordbooks")
    entries = db.relationship(
        "WordEntry", back_populates="wordbook", cascade="all, delete-orphan", order_by="WordEntry.id.asc()"
    )

    @property
    def progress(self) -> int:
        if not self.total_count:
            return 0
        return round(self.mastered_count * 100 / self.total_count)

    def to_dict(self, with_entries: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "color": self.color,
            "totalCount": self.total_count,
            "masteredCount": self.mastered_count,
            "progress": self.progress,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if with_entries:
            data["entries"] = [e.to_dict() for e in self.entries]
        return data


class WordEntry(TimestampMixin, db.Model):
    __tablename__ = "word_entries"

    id = db.Column(db.Integer, primary_key=True)
    wordbook_id = db.Column(db.Integer, db.ForeignKey("wordbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    word = db.Column(db.String(64), nullable=False)
    phonetic = db.Column(db.String(64), default="")
    meaning = db.Column(db.String(255), default="")
    example = db.Column(db.Text, default="")
    confidence = db.Column(db.Float, default=0.0, nullable=False)   # 0~1，PDF 解析置信度
    status = db.Column(db.String(16), default="new", nullable=False, index=True)  # new / learning / mastered
    review_count = db.Column(db.Integer, default=0, nullable=False)
    next_review_at = db.Column(db.DateTime, nullable=True)

    wordbook = db.relationship("Wordbook", back_populates="entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wordbookId": self.wordbook_id,
            "word": self.word,
            "phonetic": self.phonetic,
            "meaning": self.meaning,
            "example": self.example,
            "confidence": round(self.confidence, 2),
            "status": self.status,
            "statusLabel": ENTRY_STATUS_LABELS.get(self.status, self.status),
            "reviewCount": self.review_count,
            "nextReviewAt": self.next_review_at.isoformat() if self.next_review_at else None,
        }


class ReviewRecord(TimestampMixin, db.Model):
    __tablename__ = "review_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wordbook_id = db.Column(db.Integer, db.ForeignKey("wordbooks.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    word_count = db.Column(db.Integer, default=0, nullable=False)
    known_count = db.Column(db.Integer, default=0, nullable=False)
    duration_seconds = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wordbookId": self.wordbook_id,
            "date": self.date.isoformat(),
            "wordCount": self.word_count,
            "knownCount": self.known_count,
            "durationSeconds": self.duration_seconds,
        }


class Checkin(TimestampMixin, db.Model):
    __tablename__ = "checkins"
    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_checkins_user_date"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    word_count = db.Column(db.Integer, default=0, nullable=False)
    streak_snapshot = db.Column(db.Integer, default=1, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "wordCount": self.word_count,
            "streak": self.streak_snapshot,
        }


class Plan(TimestampMixin, db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(16), default="words", nullable=False)  # words / questions
    target_value = db.Column(db.Integer, default=0, nullable=False)
    period = db.Column(db.String(16), default="daily", nullable=False)       # daily / weekly
    deadline = db.Column(db.Date, nullable=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    ref_type = db.Column(db.String(16), default="wordbook")                  # wordbook / mistake
    ref_id = db.Column(db.Integer, nullable=True)

    def to_dict(self) -> dict:
        percent = round(self.progress * 100 / self.target_value) if self.target_value else 0
        return {
            "id": self.id,
            "name": self.name,
            "targetType": self.target_type,
            "targetValue": self.target_value,
            "period": self.period,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "progress": self.progress,
            "percent": min(percent, 100),
            "refType": self.ref_type,
            "refId": self.ref_id,
        }
