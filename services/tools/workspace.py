from __future__ import annotations

from pathlib import Path
from typing import Any

from services.config import config

MAX_READ_BYTES = 200_000


def workspace_root() -> Path:
    return config.workspace_root


def resolve_path(path: str, *, must_exist: bool = False) -> Path:
    """把相对路径解析到工作区内，禁止越界访问。"""
    root = workspace_root()
    raw = (path or ".").strip()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"路径超出工作区 {root_resolved}: {path}") from exc
    if must_exist and not resolved.exists():
        raise ValueError(f"路径不存在: {resolved}")
    return resolved


def tool_error(message: str, **payload: Any) -> str:
    import json

    return json.dumps({"ok": False, "error": message, **payload}, ensure_ascii=False)


def tool_ok(**payload) -> str:
    import json

    return json.dumps({"ok": True, **payload}, ensure_ascii=False)


def read_text_limited(path: Path, *, max_bytes: int = MAX_READ_BYTES) -> str:
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"文件过大 ({size} bytes)，上限 {max_bytes}")
    return path.read_text(encoding="utf-8", errors="replace")
