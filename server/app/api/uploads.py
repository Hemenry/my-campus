"""文件上传：图片与 PDF，落本地 uploads/ 目录并通过 /uploads/ 静态访问。"""

import os
import uuid

from flask import Blueprint, current_app, request

from ..image_scrub import scrub_image
from ..utils import ApiError, login_required_user, ok

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

# 魔数校验：扩展名白名单之外，再确认文件内容确实是该类型，防伪造扩展名传 HTML/脚本
MAGIC_PREFIXES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),  # 第 9~12 字节还要是 WEBP
    "pdf": (b"%PDF-",),
}
SCRUBBED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def matches_magic(ext: str, head: bytes) -> bool:
    if ext == "webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    return any(head.startswith(prefix) for prefix in MAGIC_PREFIXES.get(ext, ()))


@bp.post("")
def upload_file():
    login_required_user()
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError("没有收到文件", 422)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ApiError(f"不支持的文件类型：{ext or '未知'}", 415)

    head = file.stream.read(16)
    file.stream.seek(0)
    if not matches_magic(ext, head):
        raise ApiError("文件内容与扩展名不符", 415)

    filename = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if ext in SCRUBBED_EXTENSIONS:
        # 剥掉 EXIF（含 GPS）等元数据后再落盘，避免泄露拍摄位置等隐私
        scrubbed = scrub_image(ext, file.stream.read())
        with open(dest, "wb") as fh:
            fh.write(scrubbed)
    else:
        file.save(dest)
    return ok({"url": f"/uploads/{filename}", "filename": file.filename, "type": ext}, 201)
