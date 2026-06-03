from __future__ import annotations

import re
from pathlib import Path

from services.tools.registry import register_tool
from services.tools.workspace import (
    read_text_limited,
    resolve_path,
    tool_error,
    tool_ok,
    workspace_root,
)

MAX_LIST_ENTRIES = 500
MAX_GLOB_MATCHES = 200
MAX_GREP_MATCHES = 100
MAX_GREP_FILE_BYTES = 500_000


def _rel(path: Path) -> str:
    return str(path.relative_to(workspace_root()))


@register_tool()
def read_file(path: str) -> str:
    """读取工作区内的文本文件。path 为相对工作区的路径。"""
    try:
        resolved = resolve_path(path, must_exist=True)
        if not resolved.is_file():
            return tool_error(f"不是文件: {resolved}")
        content = read_text_limited(resolved)
        return tool_ok(path=_rel(resolved), content=content)
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def list_dir(path: str = ".") -> str:
    """列出工作区目录下的文件和子目录。path 默认为工作区根目录。"""
    try:
        resolved = resolve_path(path, must_exist=True)
        if not resolved.is_dir():
            return tool_error(f"不是目录: {resolved}")
        entries = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        truncated = len(entries) > MAX_LIST_ENTRIES
        if truncated:
            entries = entries[:MAX_LIST_ENTRIES]
        items = [
            {
                "name": p.name,
                "type": "dir" if p.is_dir() else "file",
                "path": _rel(p),
            }
            for p in entries
        ]
        return tool_ok(
            path=_rel(resolved),
            entries=items,
            truncated=truncated,
            total=len(items),
        )
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def search_files(pattern: str, path: str = ".") -> str:
    """按 glob 模式搜索文件，例如 **/*.json 或 src/**/*.tsx。"""
    try:
        base = resolve_path(path, must_exist=True)
        if not base.is_dir():
            return tool_error(f"不是目录: {base}")
        all_matches = sorted(
            (p for p in base.glob(pattern) if p.is_file()),
            key=lambda p: str(p),
        )
        truncated = len(all_matches) > MAX_GLOB_MATCHES
        matches = [_rel(p) for p in all_matches[:MAX_GLOB_MATCHES]]
        return tool_ok(
            pattern=pattern,
            path=_rel(base),
            matches=matches,
            truncated=truncated,
            total=len(all_matches),
        )
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def grep_files(
    pattern: str,
    path: str = ".",
    glob: str = "**/*",
) -> str:
    """在文件内容中搜索正则 pattern，返回匹配行。glob 限定文件范围，默认 **/*。"""
    try:
        base = resolve_path(path, must_exist=True)
        if not base.is_dir():
            return tool_error(f"不是目录: {base}")
        regex = re.compile(pattern)
        hits: list[dict[str, str | int]] = []
        for file_path in sorted(base.glob(glob)):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > MAX_GREP_FILE_BYTES:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    hits.append({"path": _rel(file_path), "line": line_no, "text": line[:300]})
                    if len(hits) >= MAX_GREP_MATCHES:
                        return tool_ok(
                            pattern=pattern,
                            path=_rel(base),
                            matches=hits,
                            truncated=True,
                        )
        return tool_ok(pattern=pattern, path=_rel(base), matches=hits, truncated=False)
    except re.error as exc:
        return tool_error(f"无效正则: {exc}")
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def write_file(path: str, content: str) -> str:
    """写入工作区内的文本文件。仅在用户明确要求修改时使用。"""
    try:
        resolved = resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return tool_ok(path=_rel(resolved), bytes=len(content.encode("utf-8")))
    except Exception as exc:
        return tool_error(str(exc))
