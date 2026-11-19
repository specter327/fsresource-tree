"""Semantic file-format categories and their extension registry."""
from __future__ import annotations
from enum import Enum
from types import MappingProxyType
from collections.abc import Iterable, Mapping

class FormatTypes(Enum):
    """High-level file-format categories, classified by filename extension."""
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    SOURCE_CODE = "source_code"
    FONT = "font"

FORMAT_EXTENSIONS: Mapping[FormatTypes, frozenset[str]] = MappingProxyType({
    FormatTypes.IMAGE: frozenset({".jpg", ".jpeg", ".jpe", ".png", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff", ".ico", ".heic", ".heif", ".avif"}),
    FormatTypes.DOCUMENT: frozenset({".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp"}),
    FormatTypes.VIDEO: frozenset({".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".mpeg", ".mpg", ".m4v", ".3gp"}),
    FormatTypes.AUDIO: frozenset({".mp3", ".wav", ".ogg", ".oga", ".flac", ".aac", ".m4a", ".wma", ".opus", ".aiff"}),
    FormatTypes.ARCHIVE: frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".zst", ".tgz", ".iso"}),
    FormatTypes.EXECUTABLE: frozenset({".exe", ".msi", ".bat", ".cmd", ".com", ".appimage", ".deb", ".rpm", ".apk", ".sh"}),
    FormatTypes.SOURCE_CODE: frozenset({".py", ".pyw", ".js", ".mjs", ".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".rs", ".go", ".rb", ".php", ".html", ".css", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml", ".sql"}),
    FormatTypes.FONT: frozenset({".ttf", ".otf", ".woff", ".woff2", ".eot"}),
})

def normalize_extensions(extensions: Iterable[str]) -> frozenset[str]:
    """Normalize extension filters to lowercase dotted suffixes."""
    if isinstance(extensions, str):
        extensions = (extensions,)
    try:
        values = tuple(extensions)
    except TypeError as error:
        raise TypeError("extensions must be an iterable of strings") from error
    normalized = set()
    for extension in values:
        if not isinstance(extension, str) or not extension.strip():
            raise TypeError("each extension must be a non-empty string")
        value = extension.strip().lower()
        normalized.add(value if value.startswith(".") else "." + value)
    return frozenset(normalized)

def normalize_formats(formats: FormatTypes | Iterable[FormatTypes]) -> frozenset[FormatTypes]:
    """Normalize one or more semantic format categories."""
    if isinstance(formats, FormatTypes):
        formats = (formats,)
    try:
        values = tuple(formats)
    except TypeError as error:
        raise TypeError("format must be a FormatTypes value or iterable") from error
    if not values or any(not isinstance(item, FormatTypes) for item in values):
        raise TypeError("format must contain one or more FormatTypes values")
    return frozenset(values)

def extensions_for(formats: FormatTypes | Iterable[FormatTypes]) -> frozenset[str]:
    """Return the union of registered extensions for requested categories."""
    categories = normalize_formats(formats)
    return frozenset().union(*(FORMAT_EXTENSIONS[item] for item in categories))

__all__ = ["FormatTypes", "FORMAT_EXTENSIONS", "normalize_extensions", "normalize_formats", "extensions_for"]
