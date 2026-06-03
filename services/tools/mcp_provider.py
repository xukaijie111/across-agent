"""从 MCP 配置加载工具，注册到 ToolRegistry（与内置 BaseTool 同一套 invoke）。"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from services.config import PROJECT_ROOT, config
from services.tools.registry import registry

logger = logging.getLogger(__name__)

_mcp_loaded = False


def _default_config_paths() -> list[Path]:
    paths: list[Path] = []
    raw = config.get("CROSSAGENT_MCP_CONFIG")
    if raw and str(raw).strip():
        p = Path(raw.strip())
        paths.append(p if p.is_absolute() else PROJECT_ROOT / p)
    paths.extend([
        PROJECT_ROOT / ".crossagent" / "mcp.json",
        PROJECT_ROOT / ".mcp.json",
    ])
    return paths


def find_mcp_config() -> Path | None:
    for path in _default_config_paths():
        if path.is_file():
            return path
    return None


def _normalize_connection(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    conn = dict(spec)
    if "transport" not in conn:
        if conn.get("url"):
            conn["transport"] = "http"
        elif conn.get("command"):
            conn["transport"] = "stdio"
        else:
            raise ValueError(
                f"MCP server {name!r} 需要 command（stdio）或 url（http）"
            )
    return conn


def parse_mcp_config(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    servers = data.get("mcpServers") or data.get("servers") or data
    if not isinstance(servers, dict):
        raise ValueError("MCP 配置格式无效：需要 mcpServers 对象")

    connections: dict[str, dict[str, Any]] = {}
    for name, spec in servers.items():
        if not isinstance(spec, dict):
            raise ValueError(f"MCP server {name!r} 配置必须是对象")
        if spec.get("disabled"):
            continue
        connections[name] = _normalize_connection(name, spec)
    return connections


def load_connections_from_file(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"MCP 配置文件必须是 JSON 对象: {path}")
    return parse_mcp_config(data)


async def _fetch_mcp_tools(connections: dict[str, dict[str, Any]]) -> list[BaseTool]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(connections, tool_name_prefix=True)
    return await client.get_tools()


def register_mcp_tools(tools: list[BaseTool], *, skip_existing: bool = True) -> list[str]:
    return registry.register_many(tools, skip_existing=skip_existing)


async def aload_mcp_tools(config_path: Path | None = None) -> list[str]:
    """异步加载 MCP 并注册。返回注册的工具名列表；失败时记录日志并返回 []。"""
    global _mcp_loaded
    if _mcp_loaded:
        return []

    path = config_path or find_mcp_config()
    if path is None:
        logger.debug("no MCP config found")
        _mcp_loaded = True
        return []

    try:
        connections = load_connections_from_file(path)
        if not connections:
            logger.info("MCP config %s has no enabled servers", path)
            _mcp_loaded = True
            return []

        tools = await _fetch_mcp_tools(connections)
        names = register_mcp_tools(tools)
        logger.info("loaded %d MCP tools from %s: %s", len(names), path, names)
        return names
    except Exception as exc:
        logger.warning("MCP load failed (%s): %s", path, exc)
        return []
    finally:
        _mcp_loaded = True


def load_mcp_tools(config_path: Path | None = None) -> list[str]:
    """同步入口（CLI / agent_loop 用）。"""
    return asyncio.run(aload_mcp_tools(config_path))


def mcp_status() -> dict[str, Any]:
    path = find_mcp_config()
    return {
        "config_path": str(path) if path else None,
        "loaded": _mcp_loaded,
    }
