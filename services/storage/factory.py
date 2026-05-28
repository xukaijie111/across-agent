from __future__ import annotations

from collections.abc import Callable

from services.config import config
from services.storage.base import StorageBackend
from services.storage.sqlite import SQLiteStorage

_storage: StorageBackend | None = None

# 以后换 Postgres 等：在这里注册，不用改 get_storage
_BACKENDS: dict[str, Callable[[], StorageBackend]] = {
    "sqlite": lambda: SQLiteStorage(config.db_path),
}


def create_storage() -> StorageBackend:
    kind = config.storage_backend
    builder = _BACKENDS.get(kind)
    if builder is None:
        supported = ", ".join(_BACKENDS)
        raise ValueError(f"未知存储类型: {kind!r}，目前支持: {supported}")
    return builder()


def get_storage() -> StorageBackend:
    """全进程唯一 Storage 实例（单例）"""
    global _storage
    if _storage is None:
        _storage = create_storage()
    return _storage


def reset_storage() -> None:
    """测试或切换配置后清空单例，下次 get_storage() 会重建"""
    global _storage
    _storage = None
