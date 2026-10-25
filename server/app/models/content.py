"""内容域模型：帖子、回答、评论、标签、点赞、收藏、资料。"""

from ..extensions import db
from .base import TimestampMixin

POST_TYPES = ("ask", "mistake", "material", "paper")
TYPE_LABELS = {
    "ask": "求助",
    "mistake": "错题",
    "material": "资料",
    "paper": "试卷",
}

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(TimestampMixin, db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    type = db.Column(db.String(16), default="topic", nullable=False)  # subject / topic
    follow_count = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "type": self.type, "followCount": self.follow_count}


class Post(TimestampMixin, db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(16), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, default="")
    images = db.Column(db.JSON, default=list)
    subject = db.Column(db.String(32), default="")
    topics = db.Column(db.JSON, default=list)
    visibility = db.Column(db.String(16), default="public", nullable=False)  # public / school / private
    status = db.Column(db.String(16), default="pending", nullable=False, index=True)  # pending / adopted / offline

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    collect_count = db.Column(db.Integer, default=0, nullable=False)
    answer_count = db.Column(db.Integer, default=0, nullable=False)
    view_count = db.Column(db.Integer, default=0, nullable=False)

    author = db.relationship("User", back_populates="posts")
    answers = db.relationship(
        "Answer", back_populates="post", cascade="all, delete-orphan", order_by="Answer.id.asc()"
    )
    tags = db.relationship("Tag", secondary=post_tags, lazy="selectin")

    def to_dict(self, detail: bool = False) -> dict:
        author = self.author
        data = {
            "id": self.id,
            "type": self.type,
            "typeLabel": TYPE_LABELS.get(self.type, self.type),
            "title": self.title,
            "content": self.content,
            "images": self.images or [],
            "subject": self.subject,
            "topics": self.topics or [],
            "visibility": self.visibility,
            "status": self.status,
            "likeCount": self.like_count,
            "collectCount": self.collect_count,
            "answerCount": self.answer_count,
            "viewCount": self.view_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "author": {
                "id": author.id,
                "nickname": author.nickname,
                "avatar": author.avatar,
                "school": author.school,
                "dept": author.dept,
            }
            if author
            else None,
        }
        if detail:
            data["answers"] = [a.to_dict() for a in self.answers]
            data["tags"] = [t.to_dict() for t in self.tags]
        return data


class Answer(TimestampMixin, db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.JSON, default=list)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    is_adopted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    post = db.relationship("Post", back_populates="answers")
    author = db.relationship("User")

    def to_dict(self) -> dict:
        author = self.author
        return {
            "id": self.id,
            "postId": self.post_id,
            "content": self.content,
            "images": self.images or [],
            "likeCount": self.like_count,
            "isAdopted": self.is_adopted,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "author": {
                "id": author.id,
                "nickname": author.nickname,
                "avatar": author.avatar,
                "school": author.school,
                "dept": author.dept,
                "adoptedCount": author.adopted_count,
            }
            if author
            else None,
        }


class Comment(TimestampMixin, db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(16), nullable=False, index=True)  # post / answer
    target_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    content = db.Column(db.String(1000), nullable=False)

    author = db.relationship("User")

    def to_dict(self) -> dict:
        author = self.author
        return {
            "id": self.id,
            "targetType": self.target_type,
            "targetId": self.target_id,
            "parentId": self.parent_id,
            "content": self.content,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "author": {"id": author.id, "nickname": author.nickname, "avatar": author.avatar} if author else None,
        }


class PostLike(TimestampMixin, db.Model):
    __tablename__ = "post_likes"
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="uq_post_likes_user_post"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)


class AnswerLike(TimestampMixin, db.Model):
    __tablename__ = "answer_likes"
    __table_args__ = (db.UniqueConstraint("user_id", "answer_id", name="uq_answer_likes_user_answer"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey("answers.id", ondelete="CASCADE"), nullable=False)


class Collection(TimestampMixin, db.Model):
    """收藏统一表：一个用户对任意类型目标只留一条。"""

    __tablename__ = "collections"
    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_collections_user_target"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = db.Column(db.String(16), nullable=False)  # post / wordbook / material / mistake
    target_id = db.Column(db.Integer, nullable=False)


class Material(TimestampMixin, db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(16), default="pdf")
    pages = db.Column(db.Integer, default=0)
    subject = db.Column(db.String(32), default="")
    grade = db.Column(db.String(16), default="")
    visibility = db.Column(db.String(16), default="public")
    audit_status = db.Column(db.String(16), default="pending")  # pending / passed / rejected
    download_count = db.Column(db.Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "postId": self.post_id,
            "filename": self.filename,
            "url": self.url,
            "fileType": self.file_type,
            "pages": self.pages,
            "subject": self.subject,
            "grade": self.grade,
            "visibility": self.visibility,
            "auditStatus": self.audit_status,
            "downloadCount": self.download_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
