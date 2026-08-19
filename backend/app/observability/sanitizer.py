import re
from typing import Any

API_KEY_PATTERNS = [
    re.compile(r"(key|secret|token|password)=([a-zA-Z0-9_-]{16,})", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9._-]{20,})", re.IGNORECASE),
]


def sanitize_message(message: str) -> str:
    """过滤敏感 Token、API Key 与内部私密信息"""
    sanitized = message
    for pattern in API_KEY_PATTERNS:
        sanitized = pattern.sub(r"\1=******", sanitized)
    return sanitized


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """递归过滤 payload 中的敏感键值与过长冗余原始文本"""
    cleaned = {}
    for k, v in payload.items():
        if any(s in k.lower() for s in ["key", "secret", "token", "password"]):
            cleaned[k] = "******"
        elif isinstance(v, dict):
            cleaned[k] = sanitize_payload(v)
        elif isinstance(v, str) and len(v) > 500:
            cleaned[k] = v[:200] + "...[内容已截断]"
        else:
            cleaned[k] = v
    return cleaned
