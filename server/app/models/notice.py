"""通知模型。"""

from ..extensions import db
from .base import TimestampMixin

NOTICE_TYPES = {
    "answer": "回答",
    "comment": "评论",
    "adopt": "采纳",
    "system": "系统",
}


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(16), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_type = db.Column(db.String(16), default="post")
    target_id = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.String(255), default="")
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])

    def to_dict(self) -> dict:
        actor = self.actor
        return {
            "id": self.id,
            "type": self.type,
            "typeLabel": NOTICE_TYPES.get(self.type, "通知"),
            "targetType": self.target_type,
            "targetId": self.target_id,
            "summary": self.summary,
            "isRead": self.is_read,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "actor": {"id": actor.id, "nickname": actor.nickname, "avatar": actor.avatar} if actor else None,
        }
