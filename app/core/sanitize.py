import re
from typing import Optional

_control_chars = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_tag_pattern = re.compile(r"<[^>]+>")


def sanitize_text(value: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """Strip control chars/tags, trim, and enforce length."""
    if value is None:
        return None

    cleaned = _control_chars.sub("", value)
    cleaned = cleaned.strip()
    cleaned = _tag_pattern.sub("", cleaned)

    if max_length is not None and max_length > 0:
        cleaned = cleaned[:max_length]
    return cleaned