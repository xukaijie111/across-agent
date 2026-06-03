from services.tools import fs, git_tools, project  # noqa: F401 — 注册内置工具
from services.tools.registry import ToolRegistry, register_tool, registry


def bootstrap_tools(*, load_mcp: bool = True) -> list[str]:
    """加载内置工具（import 时已注册）+ 可选 MCP。返回本轮新注册的 MCP 工具名。"""
    if not load_mcp:
        return []
    from services.tools.mcp_provider import load_mcp_tools

    return load_mcp_tools()


def get_tools() -> list[dict]:
    return registry.openai_tools()


def execute_tool(name: str, args: dict) -> str:
    return registry.invoke(name, args)


__all__ = [
    "ToolRegistry",
    "bootstrap_tools",
    "execute_tool",
    "get_tools",
    "register_tool",
    "registry",
]
