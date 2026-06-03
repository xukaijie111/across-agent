from __future__ import annotations

import subprocess

from services.tools.registry import register_tool
from services.tools.workspace import resolve_path, tool_error, tool_ok, workspace_root


def _run_git(args: list[str], *, timeout: int = 30) -> str:
    root = workspace_root()
    if not (root / ".git").exists():
        return tool_error("当前工作区不是 git 仓库")
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"git exit {proc.returncode}"
        return tool_error(detail)
    return tool_ok(output=proc.stdout)


@register_tool()
def git_status() -> str:
    """查看工作区 git 状态（分支与变更摘要）。"""
    try:
        return _run_git(["status", "--short", "--branch"])
    except subprocess.TimeoutExpired:
        return tool_error("git status 超时")
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def git_diff(path: str = "") -> str:
    """查看 git diff；path 可选，为相对工作区的文件或目录。"""
    try:
        args = ["diff"]
        if path.strip():
            resolved = resolve_path(path, must_exist=True)
            args.append(str(resolved.relative_to(workspace_root())))
        return _run_git(args)
    except subprocess.TimeoutExpired:
        return tool_error("git diff 超时")
    except Exception as exc:
        return tool_error(str(exc))


@register_tool()
def git_log(max_count: int = 10) -> str:
    """查看最近 git 提交记录。"""
    try:
        count = max(1, min(max_count, 50))
        return _run_git(["log", f"-{count}", "--oneline", "--decorate"])
    except subprocess.TimeoutExpired:
        return tool_error("git log 超时")
    except Exception as exc:
        return tool_error(str(exc))
