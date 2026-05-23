from enum import Enum, StrEnum


class FileTypeConstant(StrEnum):
    """MIME Type 常量类（基于 StrEnum，支持字符串特性）"""
    # 单纯字符串
    STR = "string"

    # 文本类
    TXT = "text/plain"
    HTML = "text/html"
    CSS = "text/css"
    JS = "application/javascript"
    JSON = "application/json"
    CSV = "text/csv"
    MD = "text/markdown"

    # 图片类
    JPG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"

    # 文档类
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # 压缩类
    ZIP = "application/zip"
