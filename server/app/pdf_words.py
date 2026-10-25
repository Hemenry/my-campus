"""从 PDF 词库里提取单词表。

只认带文本层的 PDF；扫描件本质是图片，提取结果为空，得先 OCR。
排版兼容顺序：竖线/制表符分隔 → 行首单词 + 音标 → 多空格表格列。
解析规则是启发式的，所以结果一律要经过用户预览确认才入库。
"""

from __future__ import annotations

import re

# 服务器可用内存约 1G。PdfReader 会把整个文件读进内存并解析全部对象，
# 所以体积、页数、词条数三道闸都要有：3MB + 30 页大约吃 100–200MB，属于安全区。
MAX_PAGES = 30
MAX_WORDS = 2000
MAX_PDF_BYTES = 3 * 1024 * 1024

# 行号：1. / 1、/ (1) / [1]
_LEADING_NOISE = re.compile(r"^\s*[（(\[]?\d{1,4}[.、)）\]．]\s*")
# 字母被 PDF 排版拆开："a b a n d o n v. 抛弃"
# 末尾必须跟空白或行尾，否则会把后面词性的首字母（v.）也吞进来变成 abandonv
_SPACED_LETTERS = re.compile(r"^((?:[A-Za-z] ){2,}[A-Za-z])(?=\s|$)")
_WORD_HEAD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
_WORD_ONLY = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")
_PHONETIC = re.compile(r"[/\[]([^/\]]{1,40}?)[/\]]")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_COLUMNS = re.compile(r"\s{2,}")
_IPA_CHARS = "əʃɪʊæʌɜθðɑɒɔˈˌŋʒːɡɹˑ"


def merge_spaced_letters(line: str) -> str:
    """PDF 常把字母间距也留成空格，行首若是连续单字母就把它们并回一个单词。"""
    match = _SPACED_LETTERS.match(line)
    if not match:
        return line
    merged = match.group(1).replace(" ", "")
    return merged + line[match.end():]


def looks_like_phonetic(text: str) -> bool:
    """判断一段文本是不是音标：不含中文，且国际音标字符出现两次以上。"""
    if not text or _CJK.search(text):
        return False
    return sum(1 for char in text if char in _IPA_CHARS) >= 2


def is_meaning(text: str) -> bool:
    """释义至少要有中文，或两个以上英文字母——否则多半是页码、序号这类噪声。"""
    if not text:
        return False
    if _CJK.search(text):
        return True
    return len(re.findall(r"[A-Za-z]", text)) >= 2


def build_entry(word: str, meaning: str, phonetic: str = "") -> dict | None:
    """组装并校验一条词条，不合法的直接丢弃（返回 None）。"""
    word = (word or "").strip()
    if not word or not _WORD_ONLY.match(word) or not 1 <= len(word) <= 64:
        return None
    meaning = (meaning or "").strip()
    if not is_meaning(meaning):
        return None
    return {
        "word": word,
        "meaning": meaning[:255],
        "phonetic": (phonetic or "").strip()[:64],
    }


def parse_line(line: str) -> dict | None:
    """解析单行。返回词条 dict，或 None 表示这行不是单词条目。"""
    line = line.strip()
    if not line:
        return None
    line = _LEADING_NOISE.sub("", line).strip()
    line = merge_spaced_letters(line).strip()
    if not line:
        return None

    # 明确分隔的情况优先，避免被后续启发式规则切坏
    if "|" in line or "｜" in line:
        parts = [p.strip() for p in re.split(r"[|｜]", line)]
        return build_entry(
            parts[0],
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "",
        )
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
        return build_entry(
            parts[0],
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "",
        )

    # 行首必须是英文单词，这一步也顺带滤掉了中文页眉和纯页码行
    match = _WORD_HEAD.match(line)
    if not match:
        return None
    word = match.group(0)
    rest = line[match.end():].strip()

    phonetic = ""
    found = _PHONETIC.search(rest)
    if found:
        phonetic = found.group(1).strip()
        rest = (rest[: found.start()] + rest[found.end():]).strip()

    # 表格排版：列之间是多个空格，第一列往往是音标
    columns = [col.strip() for col in _COLUMNS.split(rest) if col.strip()]
    if not phonetic and columns and looks_like_phonetic(columns[0]):
        phonetic = columns[0]
        columns = columns[1:]
    return build_entry(word, " ".join(columns).strip(), phonetic)


def parse_text(text: str, limit: int = MAX_WORDS) -> list[dict]:
    """逐行解析并按单词去重（保留首次出现），超过 limit 直接停。"""
    entries: list[dict] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        if len(entries) >= limit:
            break
        entry = parse_line(raw_line)
        if entry is None:
            continue
        key = entry["word"].lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


def extract_from_pdf(
    stream, max_pages: int = MAX_PAGES, max_words: int = MAX_WORDS
) -> tuple[list[dict], int, int]:
    """返回 (词条列表, PDF 总页数, 实际解析页数)。

    pypdf 不在依赖里时这里会抛 ImportError，由接口层转成 501，避免 500。
    """
    from pypdf import PdfReader  # 延迟导入：没装这个组件时模块本身仍可导入

    reader = PdfReader(stream)
    total_pages = len(reader.pages)
    used_pages = min(total_pages, max_pages)

    chunks: list[str] = []
    for index in range(used_pages):
        try:
            chunks.append(reader.pages[index].extract_text() or "")
        except Exception:
            # 个别页解析失败不影响其他页，跳过即可
            continue
    return parse_text("\n".join(chunks), max_words), total_pages, used_pages
