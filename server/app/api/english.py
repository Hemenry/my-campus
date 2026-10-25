"""英语模块：词书、词条、复习、打卡。"""

from datetime import date, datetime, timedelta

from flask import Blueprint, request
from sqlalchemy import func

from ..extensions import db
from ..models import Checkin, Plan, ReviewRecord, Wordbook, WordEntry
from ..pdf_words import MAX_PAGES, MAX_PDF_BYTES, extract_from_pdf
from ..utils import ApiError, as_int, login_required_user, ok, payload, require

bp = Blueprint("english", __name__, url_prefix="/api")


# ---------------------------------------------------------------- 词书

@bp.get("/wordbooks")
def list_wordbooks():
    user = login_required_user()
    books = (
        Wordbook.query.filter_by(user_id=user.id)
        .order_by(Wordbook.created_at.desc(), Wordbook.id.desc())
        .all()
    )
    today_end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    due_map = dict(
        db.session.query(WordEntry.wordbook_id, func.count(WordEntry.id))
        .join(Wordbook, Wordbook.id == WordEntry.wordbook_id)
        .filter(
            Wordbook.user_id == user.id,
            WordEntry.status != "mastered",
            (WordEntry.next_review_at.is_(None)) | (WordEntry.next_review_at < today_end),
        )
        .group_by(WordEntry.wordbook_id)
        .all()
    )
    return ok([{**b.to_dict(), "dueCount": due_map.get(b.id, 0)} for b in books])


def parse_words(raw_words) -> list[dict]:
    """支持结构化数组，也支持「一行一词」的纯文本粘贴。所有字段按列宽截断。"""
    words: list[dict] = []

    def as_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    if isinstance(raw_words, str):
        for line in raw_words.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
            elif "\t" in line:
                parts = [p.strip() for p in line.split("\t")]
            else:
                parts = line.split(None, 1)
            word = parts[0].strip()
            if not word:
                continue
            meaning = parts[1] if len(parts) > 1 else ""
            phonetic = parts[2] if len(parts) > 2 else ""
            words.append(
                {"word": word[:64], "meaning": meaning[:255], "phonetic": phonetic[:64]}
            )
    elif isinstance(raw_words, list):
        for item in raw_words:
            if isinstance(item, str):
                word = item.strip()
                if word:
                    words.append({"word": word[:64], "meaning": ""})
            elif isinstance(item, dict) and item.get("word"):
                words.append(
                    {
                        "word": str(item["word"]).strip()[:64],
                        "phonetic": str(item.get("phonetic") or "").strip()[:64],
                        "meaning": str(item.get("meaning") or "").strip()[:255],
                        "example": str(item.get("example") or ""),
                        "confidence": as_float(item.get("confidence")),
                    }
                )
    return words


@bp.post("/wordbooks")
def create_wordbook():
    user = login_required_user()
    data = payload()
    require(data, "name")
    words = parse_words(data.get("words") or data.get("text") or [])
    if not words:
        raise ApiError("至少需要一个单词", 422)

    book = Wordbook(
        user_id=user.id,
        name=str(data["name"]).strip()[:64],
        description=str(data.get("description") or "")[:255],
        source=str(data.get("source") or "manual")[:16],
        color=str(data.get("color") or "#1F8A6B")[:16],
        total_count=len(words),
    )
    db.session.add(book)
    db.session.flush()

    for item in words:
        db.session.add(
            WordEntry(
                wordbook_id=book.id,
                word=item["word"],
                phonetic=item.get("phonetic", ""),
                meaning=item.get("meaning", ""),
                example=item.get("example", ""),
                confidence=item.get("confidence", 0),
            )
        )
    db.session.commit()
    return ok(book.to_dict(with_entries=False), 201)


@bp.post("/wordbooks/parse-pdf")
def parse_pdf_wordbook():
    """上传 PDF 词库，解析出词条给前端预览。只解析不入库，落库走创建接口。

    识别规则是启发式的，PDF 排版千奇百怪，所以必须让用户确认后再写入。
    """
    login_required_user()
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError("没有收到文件", 422)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext != "pdf":
        raise ApiError("请上传 PDF 文件", 415)

    # 扩展名之外再验一次魔数，防止拿改名文件进来
    head = file.stream.read(8)
    file.stream.seek(0)
    if not head.startswith(b"%PDF-"):
        raise ApiError("文件内容不是 PDF", 415)

    # 体积闸：pypdf 会把整个文件读进内存，2G 机器上 8MB 的 PDF 能吃掉几百 MB，
    # 必须在解析之前拦住，不能指望解析完再看结果
    file.stream.seek(0, 2)  # 2 = SEEK_END
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_PDF_BYTES:
        limit_mb = MAX_PDF_BYTES // 1024 // 1024
        raise ApiError(f"PDF 太大（{size / 1024 / 1024:.1f} MB），请控制在 {limit_mb} MB 以内", 413)

    try:
        entries, total_pages, used_pages = extract_from_pdf(file.stream)
    except ImportError:
        raise ApiError("服务器缺少 PDF 解析组件，请联系管理员", 501)

    if not entries:
        raise ApiError(
            f"没有从这份 PDF 里识别出单词（共 {total_pages} 页）。"
            "它可能是不含文字层的扫描件，需要先做 OCR",
            422,
        )

    return ok(
        {
            "words": entries,
            "count": len(entries),
            "pageCount": total_pages,
            "parsedPages": used_pages,
            # 超过页数上限时提示用户，避免他以为整本都导进来了
            "truncated": total_pages > used_pages,
            "maxPages": MAX_PAGES,
        }
    )


@bp.get("/wordbooks/<int:book_id>")
def wordbook_detail(book_id: int):
    user = login_required_user()
    book = db.session.get(Wordbook, book_id)
    if book is None or book.user_id != user.id:
        raise ApiError("词书不存在", 404)
    return ok(book.to_dict(with_entries=True))


@bp.patch("/wordbooks/<int:book_id>")
def update_wordbook(book_id: int):
    user = login_required_user()
    book = db.session.get(Wordbook, book_id)
    if book is None or book.user_id != user.id:
        raise ApiError("词书不存在", 404)
    data = payload()
    if data.get("name"):
        book.name = str(data["name"]).strip()[:64]
    if "description" in data:
        book.description = str(data.get("description") or "")[:255]
    db.session.commit()
    return ok(book.to_dict())


@bp.delete("/wordbooks/<int:book_id>")
def delete_wordbook(book_id: int):
    user = login_required_user()
    book = db.session.get(Wordbook, book_id)
    if book is None or book.user_id != user.id:
        raise ApiError("词书不存在", 404)
    db.session.delete(book)
    db.session.commit()
    return ok({"id": book_id})


# ---------------------------------------------------------------- 复习

@bp.get("/wordbooks/<int:book_id>/review")
def review_queue(book_id: int):
    user = login_required_user()
    book = db.session.get(Wordbook, book_id)
    if book is None or book.user_id != user.id:
        raise ApiError("词书不存在", 404)

    limit = as_int(request.args.get("size"), 20, minimum=1)
    now = datetime.now()
    due = (
        WordEntry.query.filter(
            WordEntry.wordbook_id == book.id,
            WordEntry.status != "mastered",
            (WordEntry.next_review_at.is_(None)) | (WordEntry.next_review_at <= now),
        )
        .order_by(WordEntry.next_review_at.is_(None).desc(), WordEntry.id.asc())
        .limit(limit)
        .all()
    )
    if not due:
        due = (
            WordEntry.query.filter_by(wordbook_id=book.id)
            .filter(WordEntry.status != "mastered")
            .order_by(WordEntry.id.asc())
            .limit(limit)
            .all()
        )
    return ok({"book": book.to_dict(), "entries": [e.to_dict() for e in due]})


@bp.post("/wordbooks/<int:book_id>/review")
def submit_review(book_id: int):
    user = login_required_user()
    book = db.session.get(Wordbook, book_id)
    if book is None or book.user_id != user.id:
        raise ApiError("词书不存在", 404)

    data = payload()
    results = data.get("results") or []
    if not isinstance(results, list) or not results:
        raise ApiError("本次复习没有结果可以提交", 422)
    duration = as_int(data.get("durationSeconds"), 0, minimum=0)

    known = 0
    reviewed = 0
    now = datetime.now()
    for item in results:
        entry = db.session.get(WordEntry, as_int(item.get("entryId"), 0))
        if entry is None or entry.wordbook_id != book.id:
            continue
        reviewed += 1
        entry.review_count += 1
        if item.get("known"):
            known += 1
            if entry.status == "new":
                entry.status = "learning"
                entry.next_review_at = now + timedelta(days=1)
            elif entry.review_count >= 2:
                entry.status = "mastered"
                entry.next_review_at = now + timedelta(days=7)
            else:
                entry.status = "learning"
                entry.next_review_at = now + timedelta(days=2)
        else:
            entry.status = "learning"
            entry.next_review_at = now + timedelta(hours=6)

    # 只统计实际命中的词条，非法/不属于本词书的 entryId 不计入打卡与计划进度
    if reviewed == 0:
        raise ApiError("没有命中任何可复习的词条", 422)

    db.session.flush()
    book.mastered_count = WordEntry.query.filter_by(wordbook_id=book.id, status="mastered").count()

    today = date.today()
    db.session.add(
        ReviewRecord(
            user_id=user.id,
            wordbook_id=book.id,
            date=today,
            word_count=reviewed,
            known_count=known,
            duration_seconds=duration,
        )
    )
    checkin = record_checkin(user, reviewed, today)
    sync_plans(user.id, book.id, reviewed)

    db.session.commit()
    return ok(
        {
            "reviewed": reviewed,
            "known": known,
            "book": book.to_dict(),
            "checkin": checkin.to_dict(),
            "streakDays": user.streak_days,
        }
    )


def record_checkin(user, word_count: int, today: date) -> Checkin:
    """一天一条打卡记录，重复提交只累加词数；连续天数按倒序回溯。"""
    checkin = Checkin.query.filter_by(user_id=user.id, date=today).first()
    if checkin is None:
        checkin = Checkin(user_id=user.id, date=today, word_count=0, streak_snapshot=1)
        db.session.add(checkin)

    checkin.word_count += word_count

    streak = 1
    cursor = today - timedelta(days=1)
    while Checkin.query.filter_by(user_id=user.id, date=cursor).first() is not None:
        streak += 1
        cursor -= timedelta(days=1)

    checkin.streak_snapshot = streak
    user.streak_days = streak
    user.total_checkin_days = Checkin.query.filter_by(user_id=user.id).count() or 1
    db.session.flush()
    return checkin


def sync_plans(user_id: int, book_id: int, reviewed: int) -> None:
    plans = Plan.query.filter_by(user_id=user_id, ref_type="wordbook", ref_id=book_id).all()
    for plan in plans:
        plan.progress = min(plan.target_value or 0, plan.progress + reviewed)


# ---------------------------------------------------------------- 打卡

@bp.get("/checkins")
def list_checkins():
    user = login_required_user()
    # as_int 直接钳上下界：month=13 / year=0 之类的脏参数不再把 date() 撑爆成 500
    year = as_int(request.args.get("year"), date.today().year, minimum=1, maximum=9999)
    month = as_int(request.args.get("month"), date.today().month, minimum=1, maximum=12)
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    rows = (
        Checkin.query.filter(Checkin.user_id == user.id, Checkin.date >= start, Checkin.date < end)
        .order_by(Checkin.date.asc())
        .all()
    )
    return ok(
        {
            "year": year,
            "month": month,
            "days": [c.to_dict() for c in rows],
            "streakDays": user.streak_days,
            "totalCheckinDays": user.total_checkin_days,
        }
    )


@bp.post("/checkins")
def create_checkin():
    user = login_required_user()
    data = payload()
    checkin = record_checkin(user, as_int(data.get("wordCount"), 0, minimum=0), date.today())
    db.session.commit()
    return ok(checkin.to_dict(), 201)


# ---------------------------------------------------------------- 计划

@bp.get("/plans")
def list_plans():
    user = login_required_user()
    plans = Plan.query.filter_by(user_id=user.id).order_by(Plan.id.desc()).all()
    return ok([p.to_dict() for p in plans])


def parse_deadline(value):
    """把 YYYY-MM-DD 解析成 date；格式非法转 422 而不是让 ValueError 变 500。"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ApiError("截止日期格式应为 YYYY-MM-DD", 422)


@bp.post("/plans")
def create_plan():
    user = login_required_user()
    data = payload()
    require(data, "name", "targetValue")
    plan = Plan(
        user_id=user.id,
        name=str(data["name"]).strip()[:64],
        target_type=str(data.get("targetType") or "words")[:16],
        target_value=as_int(data.get("targetValue"), 0, minimum=1),
        period=str(data.get("period") or "daily")[:16],
        deadline=parse_deadline(data.get("deadline")),
        ref_type=str(data.get("refType") or "wordbook")[:16],
        ref_id=as_int(data.get("refId"), None),
    )
    db.session.add(plan)
    db.session.commit()
    return ok(plan.to_dict(), 201)


@bp.patch("/plans/<int:plan_id>")
def update_plan(plan_id: int):
    user = login_required_user()
    plan = db.session.get(Plan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise ApiError("计划不存在", 404)
    data = payload()
    if data.get("progress") is not None:
        plan.progress = as_int(data["progress"], plan.progress, minimum=0)
    if data.get("targetValue") is not None:
        plan.target_value = as_int(data["targetValue"], plan.target_value, minimum=1)
    if data.get("name"):
        plan.name = str(data["name"]).strip()[:64]
    db.session.commit()
    return ok(plan.to_dict())
