"""PDF 词库解析的单测：只覆盖纯函数，不需要 pypdf 也不需要真实 PDF 文件。

运行（在 server/ 目录下）：
    python -m unittest discover -s tests -v
"""

import io
import unittest

from app.pdf_words import (
    MAX_WORDS,
    build_entry,
    extract_from_pdf,
    is_meaning,
    looks_like_phonetic,
    merge_spaced_letters,
    parse_line,
    parse_text,
)


def build_minimal_pdf(lines):
    """手工拼一个只有文字的最小 PDF，用来验证真实的 PDF 解析链路。

    只放 ASCII：省得处理 PDF 字符串的 UTF-16 转义，释义用英文也够触发解析规则。
    """
    stream = "BT\n/F1 12 Tf\n72 720 Td\n16 TL\n"
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream += f"({escaped}) Tj T*\n"
    stream += "ET\n"
    stream_bytes = stream.encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream_bytes)).encode() + b" >>\nstream\n"
        + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_at).encode() + b"\n%%EOF\n"
    )
    return bytes(out)


class MergeSpacedLettersTest(unittest.TestCase):
    def test_joins_letters_split_by_pdf_layout(self):
        self.assertEqual(merge_spaced_letters("a b a n d o n v. 抛弃"), "abandon v. 抛弃")

    def test_leaves_normal_words_alone(self):
        self.assertEqual(merge_spaced_letters("abandon v. 抛弃"), "abandon v. 抛弃")

    def test_keeps_short_english_phrase(self):
        # "I am a boy" 不该被并成 "Iamaboy"，因为 am/boy 里的字母不是单独成块的
        self.assertEqual(merge_spaced_letters("I am a boy"), "I am a boy")


class ParseLineTest(unittest.TestCase):
    def test_pipe_separator(self):
        entry = parse_line("abandon | v. 抛弃；放弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃；放弃")
        self.assertEqual(entry["phonetic"], "")

    def test_pipe_with_three_columns(self):
        entry = parse_line("abandon | v. 抛弃 | əˈbændən")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃")
        self.assertEqual(entry["phonetic"], "əˈbændən")

    def test_tab_separator(self):
        entry = parse_line("abandon\tv. 抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_space_between_word_and_meaning(self):
        entry = parse_line("abandon v. 抛弃；放弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃；放弃")

    def test_word_directly_followed_by_chinese(self):
        entry = parse_line("abandon抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "抛弃")

    def test_slash_phonetic_is_extracted(self):
        entry = parse_line("abandon /əˈbændən/ v. 抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["phonetic"], "əˈbændən")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_bracket_phonetic_is_extracted(self):
        entry = parse_line("abandon [əˈbændən] v. 抛弃")
        self.assertEqual(entry["phonetic"], "əˈbændən")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_leading_serial_number_is_stripped(self):
        entry = parse_line("1. abandon v. 抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_parenthesised_serial_number_is_stripped(self):
        entry = parse_line("(12) coherent adj. 连贯的")
        self.assertEqual(entry["word"], "coherent")
        self.assertEqual(entry["meaning"], "adj. 连贯的")

    def test_table_columns_separated_by_multi_spaces(self):
        entry = parse_line("abandon    əˈbændən    v. 抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["phonetic"], "əˈbændən")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_spaced_out_letters_are_merged(self):
        entry = parse_line("a b a n d o n v. 抛弃")
        self.assertEqual(entry["word"], "abandon")
        self.assertEqual(entry["meaning"], "v. 抛弃")

    def test_word_only_line_without_meaning_is_dropped(self):
        self.assertIsNone(parse_line("abandon"))

    def test_meaning_of_only_pos_is_dropped(self):
        # "n." 这种只有词性没有释义，多半是噪声而非有效词条
        self.assertIsNone(parse_line("abandon n."))

    def test_chinese_header_line_is_dropped(self):
        self.assertIsNone(parse_line("第一单元 核心词汇"))

    def test_page_number_line_is_dropped(self):
        self.assertIsNone(parse_line("12"))
        self.assertIsNone(parse_line("- 12 -"))

    def test_empty_line_is_dropped(self):
        self.assertIsNone(parse_line("   "))

    def test_non_english_head_is_dropped(self):
        self.assertIsNone(parse_line("抛弃 abandon"))


class ParseTextTest(unittest.TestCase):
    def test_parses_multiple_lines(self):
        text = "abandon v. 抛弃\ncoherent adj. 连贯的\nambiguous adj. 模糊的"
        self.assertEqual(len(parse_text(text)), 3)

    def test_deduplicates_case_insensitively(self):
        text = "abandon v. 抛弃\nAbandon adj. 放任的"
        entries = parse_text(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["meaning"], "v. 抛弃")

    def test_keeps_best_entry_of_duplicates(self):
        # 重复词保留首次出现，避免后面的劣质解析覆盖掉前面的
        text = "abandon v. 抛弃\nabandon"
        self.assertEqual(len(parse_text(text)), 1)

    def test_respects_word_limit(self):
        # 用真实单词：word0/word1 里的数字会被单词正则截掉，全变成 word 而撞上去重
        words = ["abandon", "ability", "abnormal", "abolish", "abroad", "abrupt"]
        text = "\n".join(f"{w} n. 释义" for w in words)
        self.assertEqual(len(parse_text(text, limit=4)), 4)

    def test_default_limit_is_bounded(self):
        self.assertLessEqual(MAX_WORDS, 2000)

    def test_ignores_noise_lines(self):
        text = "第 1 页\nabandon v. 抛弃\n12\ncoherent adj. 连贯的"
        entries = parse_text(text)
        self.assertEqual([e["word"] for e in entries], ["abandon", "coherent"])


class HelperTest(unittest.TestCase):
    def test_phonetic_detection(self):
        self.assertTrue(looks_like_phonetic("əˈbændən"))
        self.assertTrue(looks_like_phonetic("kəʊˈhɪərənt"))
        self.assertFalse(looks_like_phonetic("v. 抛弃"))
        self.assertFalse(looks_like_phonetic(""))

    def test_meaning_detection(self):
        self.assertTrue(is_meaning("v. 抛弃"))
        self.assertTrue(is_meaning("抛弃"))
        self.assertTrue(is_meaning("n. abandonment"))
        self.assertFalse(is_meaning("1"))
        self.assertFalse(is_meaning(""))

    def test_entry_field_truncation(self):
        entry = build_entry("abandon", "释" * 400, "ə" * 100)
        self.assertEqual(len(entry["meaning"]), 255)
        self.assertEqual(len(entry["phonetic"]), 64)

    def test_overlong_word_is_rejected(self):
        self.assertIsNone(build_entry("a" * 100, "释义"))


class ExtractFromPdfTest(unittest.TestCase):
    """端到端验证：真的走一遍 pypdf 读文件 + 提文本 + 解析。"""

    def setUp(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("未安装 pypdf")

    def test_extracts_entries_from_pdf(self):
        data = build_minimal_pdf(["abandon v. give up", "coherent adj. logical"])
        entries, total_pages, used_pages = extract_from_pdf(io.BytesIO(data))
        self.assertEqual(total_pages, 1)
        self.assertEqual(used_pages, 1)
        self.assertEqual([e["word"] for e in entries], ["abandon", "coherent"])

    def test_returns_empty_when_no_word_lines(self):
        # "Page 1" 和 "12" 都是噪声，不该产出任何词条
        data = build_minimal_pdf(["Page 1", "12"])
        entries, _, _ = extract_from_pdf(io.BytesIO(data))
        self.assertEqual(entries, [])

    def test_keeps_word_meaning_split_across_layout(self):
        data = build_minimal_pdf(["1. abandon v. give up"])
        entries, _, _ = extract_from_pdf(io.BytesIO(data))
        self.assertEqual(entries, [{"word": "abandon", "meaning": "v. give up", "phonetic": ""}])

    def test_magic_prefix_present(self):
        # 接口层靠这个前缀挡掉改名的假 PDF，构造出来的文件必须带上
        self.assertTrue(build_minimal_pdf(["x"]).startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
