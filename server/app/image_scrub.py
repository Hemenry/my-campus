"""上传图片的元数据剥离：去掉 EXIF（含 GPS 定位）等隐私信息，不重新编码、不改画质。

只做字节级段手术：
- JPEG：丢弃 APP1（EXIF/XMP）与 COM 注释段，保留 JFIF/ICC/Adobe 段
- PNG：丢弃 eXIf 块
- WebP：丢弃 EXIF / XMP 块并修正 VP8X 标志位
- GIF / PDF：规范里没有 EXIF，原样保留（PDF 元数据清理超出本项目范围）
"""

JPEG_APP1 = 0xE1
JPEG_COM = 0xFE


def scrub_image(ext: str, data: bytes) -> bytes:
    if ext in ("jpg", "jpeg"):
        return scrub_jpeg(data)
    if ext == "png":
        return scrub_png(data)
    if ext == "webp":
        return scrub_webp(data)
    return data


def scrub_jpeg(data: bytes) -> bytes:
    if not data.startswith(b"\xff\xd8"):
        return data
    out = bytearray(data[:2])
    i, n = 2, len(data)
    while i < n:
        if data[i] != 0xFF:
            out += data[i:]  # 异常数据，剩余部分原样保留
            break
        while i < n and data[i] == 0xFF:  # 跳过填充 0xFF
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0xD9, 0xDA):  # EOI / SOS：之后是压缩数据
            out += b"\xff" + bytes([marker]) + data[i:]
            break
        if 0xD0 <= marker <= 0xD7:  # RSTn 无长度域
            out += b"\xff" + bytes([marker])
            continue
        if i + 2 > n:
            out += data[i - 2 :]
            break
        seg_len = int.from_bytes(data[i : i + 2], "big")
        seg_end = i + seg_len
        if seg_len < 2 or seg_end > n:
            out += data[i - 2 :]
            break
        if marker in (JPEG_APP1, JPEG_COM):
            i = seg_end  # 丢弃 EXIF/XMP 与注释
            continue
        out += b"\xff" + bytes([marker]) + data[i:seg_end]
        i = seg_end
    return bytes(out)


def scrub_png(data: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        return data
    out = bytearray(sig)
    i, n = len(sig), len(data)
    while i + 8 <= n:
        length = int.from_bytes(data[i : i + 4], "big")
        ctype = data[i + 4 : i + 8]
        chunk_end = i + 12 + length  # 长度域 + 类型 + 数据 + CRC
        if chunk_end > n:
            out += data[i:]
            break
        if ctype != b"eXIf":
            out += data[i:chunk_end]
        i = chunk_end
        if ctype == b"IEND":
            break
    return bytes(out)


def scrub_webp(data: bytes) -> bytes:
    if len(data) < 12 or not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
        return data
    out = bytearray(data[:12])
    dropped_meta = False
    i, n = 12, len(data)
    while i + 8 <= n:
        ctype = data[i : i + 4]
        size = int.from_bytes(data[i + 4 : i + 8], "little")
        chunk_end = i + 8 + size + (size & 1)  # 块按偶数字节对齐
        if chunk_end > n:
            out += data[i:]
            break
        if ctype in (b"EXIF", b"XMP "):
            dropped_meta = True
        else:
            out += data[i:chunk_end]
        i = chunk_end
    if dropped_meta:
        # VP8X 标志位：EXIF=0x08、XMP=0x04，块删掉后要把声明位一起清掉
        if out[12:16] == b"VP8X" and len(out) >= 21:
            out[20] &= ~0x0C
    out[4:8] = (len(out) - 8).to_bytes(4, "little")
    return bytes(out)
