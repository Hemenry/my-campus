"""用户模型。"""

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .base import TimestampMixin


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(32), nullable=False)
    avatar = db.Column(db.String(255), default="")
    school = db.Column(db.String(64), default="")
    dept = db.Column(db.String(64), default="")
    grade = db.Column(db.String(16), default="")
    bio = db.Column(db.String(255), default="")

    like_count = db.Column(db.Integer, default=0, nullable=False)
    adopted_count = db.Column(db.Integer, default=0, nullable=False)
    streak_days = db.Column(db.Integer, default=0, nullable=False)
    total_checkin_days = db.Column(db.Integer, default=0, nullable=False)

    posts = db.relationship("Post", back_populates="author", lazy="dynamic")
    wordbooks = db.relationship("Wordbook", back_populates="owner", lazy="dynamic")

    # --- 密码 ---
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_dict(self, with_private: bool = False) -> dict:
        """with_private 保留作接口兼容（当前公开/私有字段一致，无额外私有字段）。"""
        data = {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "school": self.school,
            "dept": self.dept,
            "grade": self.grade,
            "bio": self.bio,
            "likeCount": self.like_count,
            "adoptedCount": self.adopted_count,
            "streakDays": self.streak_days,
            "totalCheckinDays": self.total_checkin_days,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.username}>"
