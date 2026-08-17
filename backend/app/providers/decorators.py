import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class InMemoryTTLCache:
    """轻量级线程安全的 TTL 内存缓存。"""

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self._ttl = default_ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        now = time.time()
        if key in self._store:
            expire_at, value = self._store[key]
            if now < expire_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expire_at = time.time() + (ttl or self._ttl)
        self._store[key] = (expire_at, value)

    def clear(self) -> None:
        self._store.clear()