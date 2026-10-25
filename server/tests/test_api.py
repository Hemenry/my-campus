"""API 回归测试：针对 2026-10-21 代码审查修复项的回归覆盖。

运行（在 server/ 目录下，用项目 venv）：
    python -m unittest discover -s tests -v
使用 SQLite 内存库，不需要真实 MySQL。
"""

import os  # noqa: E402
import tempfile  # noqa: E402

# 必须在 import app 之前准备好环境，config 在导入期就会校验密钥
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("FLASK_DEBUG", "1")

import unittest  # noqa: E402
import warnings  # noqa: E402

warnings.filterwarnings("ignore", category=ResourceWarning)  # sqlite 内存库连接随 GC 关闭的提示

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Notification, Post, ReviewRecord, WordEntry  # noqa: E402

TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="geekcampus-test-uploads-")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    UPLOAD_FOLDER = TEST_UPLOAD_DIR
    JWT_ACCESS_TOKEN_EXPIRES = Config.JWT_ACCESS_TOKEN_EXPIRES


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ---- helpers ----
    def register(self, username="alice", password="secret66"):
        resp = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "nickname": username},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()["data"]["token"]

    def create_post(self, token, **kwargs):
        payload = {"title": "测试帖", "type": "ask", "visibility": "public"}
        payload.update(kwargs)
        resp = self.client.post("/api/posts", json=payload, headers=auth(token))
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()["data"]


class TestAuth(ApiTestCase):
    def test_register_and_login(self):
        token = self.register()
        resp = self.client.get("/api/auth/me", headers=auth(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["username"], "alice")

        login = self.client.post(
            "/api/auth/login", json={"username": "alice", "password": "secret66"}
        )
        self.assertEqual(login.status_code, 200)

    def test_update_me_truncates_to_column_width(self):
        """nickname 列宽 32：超长输入截断而不是 1406 → 500。"""
        token = self.register()
        resp = self.client.patch(
            "/api/auth/me", json={"nickname": "n" * 100, "school": "s" * 200}, headers=auth(token)
        )
        self.assertEqual(resp.status_code, 200, resp.get_json())
        data = resp.get_json()["data"]
        self.assertEqual(len(data["nickname"]), 32)
        self.assertEqual(len(data["school"]), 64)

    def test_login_rate_limited(self):
        """连续失败 5 次后 429，防止撞库（用独立用户名避免污染其他用例的限流窗口）。"""
        self.register("brute", "secret66")
        for _ in range(5):
            resp = self.client.post(
                "/api/auth/login", json={"username": "brute", "password": "wrong-pass"}
            )
            self.assertEqual(resp.status_code, 401)
        resp = self.client.post(
            "/api/auth/login", json={"username": "brute", "password": "wrong-pass"}
        )
        self.assertEqual(resp.status_code, 429)


class TestPostVisibility(ApiTestCase):
    """High #1：非 public 帖子不能被猜 ID 读取 / 互动。"""

    def _private_post(self, visibility):
        token_a = self.register("owner")
        post = self.create_post(token_a, visibility=visibility)
        return token_a, post["id"]

    def _assert_hidden(self, post_id):
        resp = self.client.get(f"/api/posts/{post_id}")
        self.assertEqual(resp.status_code, 404)
        token_b = self.register("visitor")
        resp = self.client.get(f"/api/posts/{post_id}", headers=auth(token_b))
        self.assertEqual(resp.status_code, 404)
        # 评论列表同样要走可见性校验
        resp = self.client.get(
            "/api/comments", query_string={"targetType": "post", "targetId": post_id}
        )
        self.assertEqual(resp.status_code, 404)
        # 互动接口也不放行
        resp = self.client.post(f"/api/posts/{post_id}/like", headers=auth(token_b))
        self.assertEqual(resp.status_code, 404)

    def test_private_post_hidden_from_others(self):
        token_a, post_id = self._private_post("private")
        self._assert_hidden(post_id)
        # 作者本人可见
        resp = self.client.get(f"/api/posts/{post_id}", headers=auth(token_a))
        self.assertEqual(resp.status_code, 200)

    def test_school_post_hidden_from_others(self):
        _, post_id = self._private_post("school")
        self._assert_hidden(post_id)

    def test_public_post_still_open(self):
        token_a = self.register("owner")
        post = self.create_post(token_a, visibility="public")
        resp = self.client.get(f"/api/posts/{post['id']}")
        self.assertEqual(resp.status_code, 200)


class TestPostInteraction(ApiTestCase):
    def test_toggle_like_idempotent_counts(self):
        token = self.register()
        post = self.create_post(token)
        resp = self.client.post(f"/api/posts/{post['id']}/like", headers=auth(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"], {"liked": True, "likeCount": 1})
        resp = self.client.post(f"/api/posts/{post['id']}/like", headers=auth(token))
        self.assertEqual(resp.get_json()["data"], {"liked": False, "likeCount": 0})

    def test_view_count_dedup_per_session(self):
        """同一会话重复打开详情，浏览数只 +1。"""
        token = self.register()
        post = self.create_post(token)
        self.client.get(f"/api/posts/{post['id']}", headers=auth(token))
        first = db.session.get(Post, post["id"]).view_count
        self.client.get(f"/api/posts/{post['id']}", headers=auth(token))
        second = db.session.get(Post, post["id"]).view_count
        self.assertEqual(first, 1)
        self.assertEqual(second, 1)


class TestComments(ApiTestCase):
    def test_orphan_comment_rejected(self):
        token = self.register()
        resp = self.client.post(
            "/api/comments",
            json={"targetType": "post", "targetId": 9999, "content": "hi"},
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 404)

    def test_parent_comment_must_match_target(self):
        token = self.register()
        post_a = self.create_post(token, title="帖 A")
        post_b = self.create_post(token, title="帖 B")
        resp = self.client.post(
            "/api/comments",
            json={"targetType": "post", "targetId": post_a["id"], "content": "一层"},
            headers=auth(token),
        )
        parent_id = resp.get_json()["data"]["id"]

        resp = self.client.post(
            "/api/comments",
            json={
                "targetType": "post",
                "targetId": post_b["id"],
                "content": "挂错目标",
                "parentId": parent_id,
            },
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 422)


class TestEnglish(ApiTestCase):
    def _create_wordbook(self, token, words):
        resp = self.client.post(
            "/api/wordbooks",
            json={"name": "六级", "words": words},
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()["data"]

    def test_word_import_truncates_and_survives_bad_confidence(self):
        token = self.register()
        long_word = "w" * 200
        book = self._create_wordbook(
            token,
            [
                {"word": long_word, "meaning": "m" * 500, "confidence": "high"},
                "短词|简短释义",
            ],
        )
        entry = WordEntry.query.filter_by(wordbook_id=book["id"]).first()
        self.assertEqual(len(entry.word), 64)
        self.assertEqual(len(entry.meaning), 255)
        self.assertEqual(entry.confidence, 0.0)

    def test_text_paste_truncates(self):
        token = self.register()
        book = self._create_wordbook(token, f"{'x' * 120}|{'y' * 400}")
        entry = WordEntry.query.filter_by(wordbook_id=book["id"]).first()
        self.assertEqual(len(entry.word), 64)
        self.assertEqual(len(entry.meaning), 255)

    def test_plan_deadline_invalid_is_422(self):
        token = self.register()
        resp = self.client.post(
            "/api/plans",
            json={"name": "计划", "targetValue": 30, "deadline": "2026-13-01"},
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 422)
        resp = self.client.post(
            "/api/plans",
            json={"name": "计划", "targetValue": 30, "deadline": "2026/12/01"},
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 422)

    def test_checkin_month_out_of_range_clamped(self):
        token = self.register()
        resp = self.client.get(
            "/api/checkins", query_string={"year": "2026", "month": "13"}, headers=auth(token)
        )
        self.assertEqual(resp.status_code, 200, resp.get_json())
        self.assertEqual(resp.get_json()["data"]["month"], 12)
        resp = self.client.get(
            "/api/checkins", query_string={"year": "0", "month": "0"}, headers=auth(token)
        )
        self.assertEqual(resp.status_code, 200)

    def test_review_counts_only_matched_entries(self):
        """复习统计按实际命中词条计数，脏 entryId 不虚增打卡词数。"""
        token = self.register()
        book = self._create_wordbook(token, ["alpha|第一", "beta|第二"])
        entry_id = WordEntry.query.filter_by(wordbook_id=book["id"]).first().id

        resp = self.client.post(
            f"/api/wordbooks/{book['id']}/review",
            json={
                "results": [
                    {"entryId": entry_id, "known": True},
                    {"entryId": entry_id + 999, "known": True},
                    {"entryId": "abc", "known": False},
                ],
                "durationSeconds": 60,
            },
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 200, resp.get_json())
        data = resp.get_json()["data"]
        self.assertEqual(data["reviewed"], 1)
        self.assertEqual(data["known"], 1)
        record = ReviewRecord.query.filter_by(user_id=1).first()
        self.assertEqual(record.word_count, 1)

    def test_review_all_invalid_rejected(self):
        token = self.register()
        book = self._create_wordbook(token, ["alpha|第一"])
        resp = self.client.post(
            f"/api/wordbooks/{book['id']}/review",
            json={"results": [{"entryId": 999999, "known": True}]},
            headers=auth(token),
        )
        self.assertEqual(resp.status_code, 422)


class TestNotifications(ApiTestCase):
    def test_mark_read_with_bad_ids_is_422(self):
        token = self.register()
        resp = self.client.post(
            "/api/notifications/read", json={"ids": ["abc"]}, headers=auth(token)
        )
        self.assertEqual(resp.status_code, 422)

    def test_mark_read_with_mixed_ids_uses_valid_only(self):
        token = self.register()
        user_id = 1
        db.session.add(Notification(recipient_id=user_id, type="system", target_type="system", summary="x"))
        db.session.commit()
        resp = self.client.post(
            "/api/notifications/read", json={"ids": ["abc", 1]}, headers=auth(token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["updated"], 1)


class TestStats(ApiTestCase):
    def test_user_profile_requires_login_and_hides_username(self):
        self.register("owner")
        resp = self.client.get("/api/users/1")
        self.assertEqual(resp.status_code, 401)

        token = self.register("viewer")
        resp = self.client.get("/api/users/1", headers=auth(token))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("username", resp.get_json()["data"])
        # 本人可见 username
        resp = self.client.get("/api/users/2", headers=auth(token))
        self.assertEqual(resp.get_json()["data"]["username"], "viewer")

    def test_due_words_excludes_future_schedule(self):
        token = self.register()
        resp = self.client.post(
            "/api/wordbooks",
            json={"name": "词书", "words": ["a|1", "b|2"]},
            headers=auth(token),
        )
        book = resp.get_json()["data"]
        entries = WordEntry.query.filter_by(wordbook_id=book["id"]).all()
        from datetime import datetime, timedelta

        entries[0].next_review_at = datetime.now() - timedelta(hours=1)  # 已到期
        entries[1].next_review_at = datetime.now() + timedelta(days=30)  # 未到期
        db.session.commit()

        resp = self.client.get("/api/stats/summary", headers=auth(token))
        self.assertEqual(resp.get_json()["data"]["dueWords"], 1)


class TestUploads(ApiTestCase):
    def test_fake_image_rejected_by_magic_bytes(self):
        token = self.register()
        from io import BytesIO

        data = {"file": (BytesIO(b"<html>not an image</html>"), "x.png")}
        resp = self.client.post(
            "/api/uploads", data=data, headers=auth(token), content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 415)

    def test_real_png_accepted_and_exif_stripped(self):
        token = self.register()
        from io import BytesIO

        # 最小合法 PNG（1x1 透明），头部手工合成，带伪造 eXIf 块验证剥离
        import struct
        import zlib

        def chunk(ctype, payload):
            return (
                struct.pack(">I", len(payload))
                + ctype
                + payload
                + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
            )

        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        idat = chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x01"))
        exif = chunk(b"eXIf", b"Exif\x00\x00fake-gps")
        iend = chunk(b"IEND", b"")
        blob = b"\x89PNG\r\n\x1a\n" + ihdr + exif + idat + iend

        data = {"file": (BytesIO(blob), "photo.png")}
        resp = self.client.post(
            "/api/uploads", data=data, headers=auth(token), content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        url = resp.get_json()["data"]["url"]
        self.assertNotEqual(url.find("/uploads/"), -1)

        from app.image_scrub import scrub_png

        saved = os.path.join(self.app.config["UPLOAD_FOLDER"], url.rsplit("/", 1)[-1])
        with open(saved, "rb") as fh:
            content = fh.read()
        self.assertNotIn(b"fake-gps", content)
        self.assertTrue(content.startswith(b"\x89PNG"))
        self.assertEqual(scrub_png(blob), content)


if __name__ == "__main__":
    unittest.main()
